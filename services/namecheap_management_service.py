import os
import requests
import xmltodict
from dotenv import load_dotenv
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import HTTPException

from models.api_dto import (
    DNSRecordResponse,
    DomainInfoResponse,
    DNSRecordRequest,
    DomainStatusResponse
)


class NamecheapManagementService:
    """
    Service class responsible for interacting with the Namecheap API.
    It handles retrieving domain information, DNS management, URL forwarding,
    and basic hosting setup using Namecheap's XML API.
    """

    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # Authentication and API configuration
        self.api_user = os.getenv("API_USER")            # API user
        self.api_key = os.getenv("API_KEY")              # API key
        self.username = os.getenv("NAMEOFUSER")          # Namecheap username
        self.client_ip = os.getenv("CLIENT_IP")          # Registered client IP

        # Determine whether to use production or sandbox API
        use_production = os.getenv("NAMECHEAP_USE_PRODUCTION", "false").lower() == "true"
        self.api_url = (
            "https://api.namecheap.com/xml.response" if use_production
            else "https://api.sandbox.namecheap.com/xml.response"
        )

        # Default IP used when configuring hosting records
        self.default_hosting_ip = os.getenv("DEFAULT_HOSTING_IP", "34.123.45.6")

    def _build_api_url(self, command: str, **params) -> str:
        """
        Constructs the full Namecheap API URL with common parameters.

        Args:
            command: The Namecheap API command to execute.
            params: Additional command-specific parameters.

        Returns:
            A fully constructed request URL.
        """
        base_url = (
            f"{self.api_url}?ApiUser={self.api_user}&ApiKey={self.api_key}"
            f"&UserName={self.username}&ClientIp={self.client_ip}&Command={command}"
        )
        # Append additional params
        for key, value in params.items():
            base_url += f"&{key}={value}"
        return base_url

    def _make_api_request(self, url: str) -> Dict:
        """
        Sends a GET request to the Namecheap API and parses the XML response.

        Args:
            url: Fully constructed request URL.

        Returns:
            Parsed XML response converted to a Python dictionary.

        Raises:
            HTTPException: If API returns an error or the request fails.
        """
        try:
            response = requests.get(url, timeout=30)  # Send GET request
            response.raise_for_status()               # Raise if status is not 200

            # Parse XML to dictionary
            data = xmltodict.parse(response.text)

            # Detect Namecheap API-reported errors
            api_response = data.get('ApiResponse', {})
            if api_response.get('@Status') == 'ERROR':
                errors = api_response.get('Errors', {}).get('Error', [])
                if isinstance(errors, dict):
                    errors = [errors]
                error_messages = [e.get('#text', 'Unknown error') for e in errors]
                raise HTTPException(
                    status_code=502,
                    detail=f"Namecheap API Error: {'; '.join(error_messages)}"
                )

            return data

        except requests.exceptions.RequestException as e:
            # Network/connection issues
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to Namecheap API: {str(e)}"
            )
        except Exception as e:
            # Any unexpected parsing or runtime error
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )

    def get_domain_info(self, sld: str, tld: str, username: str) -> DomainInfoResponse:
        """
        Retrieves general information about a domain including owner, expiry,
        nameservers, status, and WhoisGuard.

        Args:
            sld: Second-level domain (example in example.com)
            tld: Top-level domain (com in example.com)
            username: User requesting data

        Returns:
            DomainInfoResponse with detailed domain information.
        """
        url = self._build_api_url(
            "namecheap.domains.getInfo",
            DomainName=f"{sld}.{tld}"
        )

        data = self._make_api_request(url)

        # Extract domain section from response
        cmd_response = data['ApiResponse']['CommandResponse']
        domain_info = cmd_response['DomainGetInfoResult']

        # Parse important dates
        created_date = self._parse_date(domain_info.get('@CreatedDate'))
        expires_date = self._parse_date(domain_info.get('@ExpiredDate'))

        # Extract nameserver list
        nameservers_data = domain_info.get('DnsDetails', {}).get('Nameserver', [])
        if isinstance(nameservers_data, dict):
            nameservers_data = [nameservers_data]
        nameservers = [ns.get('#text', '') for ns in nameservers_data if isinstance(ns, dict)]

        return DomainInfoResponse(
            domain_name=f"{sld}.{tld}",
            owner_name=domain_info.get('@OwnerName', ''),
            is_owner=domain_info.get('@IsOwner', 'false').lower() == 'true',
            status=domain_info.get('@Status', 'Unknown'),
            created_date=created_date,
            expires_date=expires_date,
            is_locked=domain_info.get('@IsLocked', 'false').lower() == 'true',
            auto_renew=domain_info.get('@AutoRenew', 'false').lower() == 'true',
            whoisguard_enabled=domain_info.get('Whoisguard', {}).get('@Enabled', 'false').lower() == 'true',
            is_premium=domain_info.get('@IsPremium', 'false').lower() == 'true',
            nameservers=nameservers
        )

    def get_dns_records(self, sld: str, tld: str) -> List[DNSRecordResponse]:
        """
        Retrieves all DNS records associated with a domain.

        Args:
            sld: Second-level domain
            tld: Top-level domain

        Returns:
            A list of DNSRecordResponse objects.
        """
        url = self._build_api_url(
            "namecheap.domains.dns.getHosts",
            SLD=sld,
            TLD=tld
        )

        data = self._make_api_request(url)

        cmd_response = data['ApiResponse']['CommandResponse']
        hosts_data = cmd_response['DomainDNSGetHostsResult'].get('host', [])

        # Normalize to list
        if isinstance(hosts_data, dict):
            hosts_data = [hosts_data]

        dns_records = []
        for host in hosts_data:
            dns_records.append(DNSRecordResponse(
                host_id=host.get('@HostId'),
                hostname=host.get('@Name', ''),
                record_type=host.get('@Type', ''),
                address=host.get('@Address', ''),
                ttl=int(host.get('@TTL', 1800)),
                mx_pref=int(host.get('@MXPref', 10)) if host.get('@MXPref') else None,
                is_active=host.get('@IsActive', 'true').lower() == 'true'
            ))

        return dns_records

    def update_dns_records(self, sld: str, tld: str, records: List[DNSRecordRequest]) -> List[DNSRecordResponse]:
        """
        Replaces ALL DNS records on a domain with a new set.

        Args:
            sld: Second-level domain
            tld: Top-level domain
            records: DNS records to apply

        Returns:
            Updated list of DNSRecordResponse.
        """
        if not records:
            raise HTTPException(
                status_code=400,
                detail="At least one DNS record is required"
            )

        params = {"SLD": sld, "TLD": tld}

        # Construct Namecheap setHosts parameter set
        for idx, record in enumerate(records, start=1):
            params[f"HostName{idx}"] = record.hostname
            params[f"RecordType{idx}"] = record.record_type
            params[f"Address{idx}"] = record.address
            params[f"TTL{idx}"] = str(record.ttl)

            if record.record_type == "MX":  # MX needs extra priority field
                params[f"MXPref{idx}"] = str(record.mx_pref)

        url = self._build_api_url("namecheap.domains.dns.setHosts", **params)
        self._make_api_request(url)

        # Return updated DNS list
        return self.get_dns_records(sld, tld)

    def set_url_forwarding(self, sld: str, tld: str, target_url: str, forward_type: str = "permanent") -> Dict:
        """
        Enables URL forwarding for a domain by creating a URL record.

        Args:
            sld: Second-level domain
            tld: Top-level domain
            target_url: URL to redirect to
            forward_type: 301 (permanent) or 302 (temporary)

        Returns:
            Success message dictionary.
        """
        # Use '@' to forward root domain
        url = self._build_api_url(
            "namecheap.domains.dns.setHosts",
            SLD=sld,
            TLD=tld,
            HostName1="@",
            RecordType1="URL",
            Address1=target_url,
            TTL1="100"
        )

        # Append forwarding type
        url += "&URLForwardingType=301" if forward_type == "permanent" else "&URLForwardingType=302"

        self._make_api_request(url)

        return {
            "success": True,
            "message": f"URL forwarding set to {target_url}",
            "forward_type": forward_type
        }

    def set_hosting(self, sld: str, tld: str, custom_ip: Optional[str] = None) -> Dict:
        """
        Configures DNS for basic hosting, including A record and CNAME.

        Args:
            sld: Second-level domain
            tld: Top-level domain
            custom_ip: Optional custom hosting IP

        Returns:
            Dictionary describing applied hosting configuration.
        """
        hosting_ip = custom_ip or self.default_hosting_ip

        hosting_records = [
            DNSRecordRequest(  # A record for root domain
                hostname="@",
                record_type="A",
                address=hosting_ip,
                ttl=1800
            ),
            DNSRecordRequest(  # CNAME for www
                hostname="www",
                record_type="CNAME",
                address=f"{sld}.{tld}.",
                ttl=1800
            )
        ]

        updated_records = self.update_dns_records(sld, tld, hosting_records)

        return {
            "success": True,
            "message": f"Hosting configured with IP {hosting_ip}",
            "dns_records_set": updated_records
        }

    def get_domain_status(self, sld: str, tld: str, username: str) -> DomainStatusResponse:
        """
        Combines domain info and DNS info into a unified status overview.

        Args:
            sld: Second-level domain
            tld: Top-level domain
            username: Requesting user

        Returns:
            DomainStatusResponse object containing combined info.
        """
        domain_info = self.get_domain_info(sld, tld, username)
        dns_records = self.get_dns_records(sld, tld)

        # Determine hosting presence (A record on root)
        is_hosted = any(
            r.hostname == "@" and r.record_type == "A" for r in dns_records
        )

        # Determine forwarding presence (URL record)
        is_forwarding = any(
            r.record_type == "URL" for r in dns_records
        )

        return DomainStatusResponse(
            domain_info=domain_info,
            dns_records=dns_records,
            is_hosted=is_hosted,
            is_forwarding=is_forwarding
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Converts Namecheap date string (MM/DD/YYYY) into a datetime object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%m/%d/%Y")
        except (ValueError, TypeError):
            return None

# ==============================================
# NamecheapManagementService (Fully Commented)
# ==============================================

import os
import requests
import xmltodict
from dotenv import load_dotenv
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import HTTPException

from models.api_dto import (
    DNSRecordResponse,
    DomainInfoResponse,
    DNSRecordRequest,
    DomainStatusResponse
)


class NamecheapManagementService:
    """
    Service responsible for communicating with the Namecheap API.
    Handles:
    - Domain information retrieval
    - DNS record management
    - URL forwarding setup
    - Basic hosting configuration
    """

    def __init__(self):
        # Load environment variables from .env
        load_dotenv()

        # Namecheap API authentication
        self.api_user = os.getenv("API_USER")
        self.api_key = os.getenv("API_KEY")
        self.username = os.getenv("NAMEOFUSER")
        self.client_ip = os.getenv("CLIENT_IP")

        # Switch between sandbox & production environments
        use_production = os.getenv("NAMECHEAP_USE_PRODUCTION", "false").lower() == "true"
        self.api_url = (
            "https://api.namecheap.com/xml.response" if use_production
            else "https://api.sandbox.namecheap.com/xml.response"
        )

        # Default IP used for hosting when setting A record
        self.default_hosting_ip = os.getenv("DEFAULT_HOSTING_IP", "34.123.45.6")

    def _build_api_url(self, command: str, **params) -> str:
        """
        Builds a Namecheap API request URL.
        All API calls require these base parameters.
        Additional parameters are appended dynamically.
        """
        base_url = (
            f"{self.api_url}?ApiUser={self.api_user}&ApiKey={self.api_key}"
            f"&UserName={self.username}&ClientIp={self.client_ip}&Command={command}"
        )

        # Add extra parameters (SLD, TLD, HostName, etc.)
        for key, value in params.items():
            base_url += f"&{key}={value}"

        return base_url

    def _make_api_request(self, url: str) -> Dict:
        """
        Sends a GET request to the Namecheap API.
        Converts XML response into Python dictionary.
        Handles:
            - HTTP request errors
            - Namecheap API internal errors
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse returned XML to dictionary
            data = xmltodict.parse(response.text)

            api_response = data.get('ApiResponse', {})

            # If Namecheap returns an error
            if api_response.get('@Status') == 'ERROR':
                errors = api_response.get('Errors', {}).get('Error', [])
                if isinstance(errors, dict):  # single error
                    errors = [errors]
                error_messages = [e.get('#text', 'Unknown error') for e in errors]

                raise HTTPException(
                    status_code=502,
                    detail=f"Namecheap API Error: {'; '.join(error_messages)}"
                )

            return data

        except requests.exceptions.RequestException as e:
            # Network errors
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to Namecheap API: {str(e)}"
            )
        except Exception as e:
            # Unexpected errors
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )

    def get_domain_info(self, sld: str, tld: str, username: str) -> DomainInfoResponse:
        """
        Fetches detailed domain information from Namecheap.
        Includes owner info, creation/expiry date, lock status, etc.
        """
        url = self._build_api_url(
            "namecheap.domains.getInfo",
            DomainName=f"{sld}.{tld}"
        )

        data = self._make_api_request(url)

        cmd_response = data['ApiResponse']['CommandResponse']
        domain_info = cmd_response['DomainGetInfoResult']

        created_date = self._parse_date(domain_info.get('@CreatedDate'))
        expires_date = self._parse_date(domain_info.get('@ExpiredDate'))

        # Parse nameservers
        nameservers_data = domain_info.get('DnsDetails', {}).get('Nameserver', [])
        if isinstance(nameservers_data, dict):
            nameservers_data = [nameservers_data]
        nameservers = [ns.get('#text', '') for ns in nameservers_data if isinstance(ns, dict)]

        return DomainInfoResponse(
            domain_name=f"{sld}.{tld}",
            owner_name=domain_info.get('@OwnerName', ''),
            is_owner=domain_info.get('@IsOwner', 'false').lower() == 'true',
            status=domain_info.get('@Status', 'Unknown'),
            created_date=created_date,
            expires_date=expires_date,
            is_locked=domain_info.get('@IsLocked', 'false').lower() == 'true',
            auto_renew=domain_info.get('@AutoRenew', 'false').lower() == 'true',
            whoisguard_enabled=domain_info.get('Whoisguard', {}).get('@Enabled', 'false').lower() == 'true',
            is_premium=domain_info.get('@IsPremium', 'false').lower() == 'true',
            nameservers=nameservers
        )

    def get_dns_records(self, sld: str, tld: str) -> List[DNSRecordResponse]:
        """
        Retrieves full DNS host record list for a domain.
        """
        url = self._build_api_url(
            "namecheap.domains.dns.getHosts",
            SLD=sld,
            TLD=tld
        )

        data = self._make_api_request(url)

        cmd_response = data['ApiResponse']['CommandResponse']
        hosts_data = cmd_response['DomainDNSGetHostsResult'].get('host', [])

        if isinstance(hosts_data, dict):
            hosts_data = [hosts_data]

        dns_records = []
        for host in hosts_data:
            dns_records.append(DNSRecordResponse(
                host_id=host.get('@HostId'),
                hostname=host.get('@Name', ''),
                record_type=host.get('@Type', ''),
                address=host.get('@Address', ''),
                ttl=int(host.get('@TTL', 1800)),
                mx_pref=int(host.get('@MXPref', 10)) if host.get('@MXPref') else None,
                is_active=host.get('@IsActive', 'true').lower() == 'true'
            ))

        return dns_records

    def update_dns_records(self, sld: str, tld: str, records: List[DNSRecordRequest]) -> List[DNSRecordResponse]:
        """
        Updates domain DNS records.
        NOTE: Namecheap REPLACES ALL EXISTING RECORDS in one request.
        """
        if not records:
            raise HTTPException(
                status_code=400,
                detail="At least one DNS record is required"
            )

        params = {"SLD": sld, "TLD": tld}

        # Namecheap expects HostName1, HostName2, ...
        for idx, record in enumerate(records, start=1):
            params[f"HostName{idx}"] = record.hostname
            params[f"RecordType{idx}"] = record.record_type
            params[f"Address{idx}"] = record.address
            params[f"TTL{idx}"] = str(record.ttl)

            if record.record_type == "MX":
                params[f"MXPref{idx}"] = str(record.mx_pref)

        url = self._build_api_url("namecheap.domains.dns.setHosts", **params)
        self._make_api_request(url)

        # Return updated DNS list
        return self.get_dns_records(sld, tld)

    def set_url_forwarding(self, sld: str, tld: str, target_url: str, forward_type: str = "permanent") -> Dict:
        """
        Enables URL forwarding for a domain.
        Creates a record of type URL.
        """
        url = self._build_api_url(
            "namecheap.domains.dns.setHosts",
            SLD=sld,
            TLD=tld,
            HostName1="@",
            RecordType1="URL",
            Address1=target_url,
            TTL1="100"
        )

        # 301 = permanent, 302 = temporary
        if forward_type == "permanent":
            url += "&URLForwardingType=301"
        else:
            url += "&URLForwardingType=302"

        self._make_api_request(url)

        return {
            "success": True,
            "message": f"URL forwarding set to {target_url}",
            "forward_type": forward_type
        }

    def set_hosting(self, sld: str, tld: str, custom_ip: Optional[str] = None) -> Dict:
        """
        Quickly configures basic hosting by setting A + CNAME records.
        """
        hosting_ip = custom_ip or self.default_hosting_ip

        hosting_records = [
            DNSRecordRequest(
                hostname="@",
                record_type="A",
                address=hosting_ip,
                ttl=1800
            ),
            DNSRecordRequest(
                hostname="www",
                record_type="CNAME",
                address=f"{sld}.{tld}.",
                ttl=1800
            )
        ]

        updated_records = self.update_dns_records(sld, tld, hosting_records)

        return {
            "success": True,
            "message": f"Hosting configured with IP {hosting_ip}",
            "dns_records_set": updated_records
        }

    def get_domain_status(self, sld: str, tld: str, username: str) -> DomainStatusResponse:
        """
        Combines domain info + DNS + hosting/forwarding detection.
        """
        domain_info = self.get_domain_info(sld, tld, username)
        dns_records = self.get_dns_records(sld, tld)

        is_hosted = any(
            r.hostname == "@" and r.record_type == "A"
            for r in dns_records
        )

        is_forwarding = any(
            r.record_type == "URL"
            for r in dns_records
        )

        return DomainStatusResponse(
            domain_info=domain_info,
            dns_records=dns_records,
            is_hosted=is_hosted,
            is_forwarding=is_forwarding
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Namecheap returns dates as MM/DD/YYYY.
        Converts to Python datetime.
        """
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%m/%d/%Y")
        except (ValueError, TypeError):
            return None

