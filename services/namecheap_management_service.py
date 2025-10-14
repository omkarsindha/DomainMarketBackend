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
    Service for managing domains via Namecheap API.
    Handles domain info retrieval, DNS management, forwarding, and hosting setup.
    """

    def __init__(self):
        load_dotenv()

        self.api_user = os.getenv("API_USER")
        self.api_key = os.getenv("API_KEY")
        self.username = os.getenv("NAMEOFUSER")
        self.client_ip = os.getenv("CLIENT_IP")

        # Use sandbox by default, switch to production via env var
        use_production = os.getenv("NAMECHEAP_USE_PRODUCTION", "false").lower() == "true"
        self.api_url = (
            "https://api.namecheap.com/xml.response" if use_production
            else "https://api.sandbox.namecheap.com/xml.response"
        )

        # Default IP for hosting (can be configured via env)
        self.default_hosting_ip = os.getenv("DEFAULT_HOSTING_IP", "34.123.45.6")

    def _build_api_url(self, command: str, **params) -> str:
        """Builds a Namecheap API request URL with common parameters."""
        base_url = (
            f"{self.api_url}?ApiUser={self.api_user}&ApiKey={self.api_key}"
            f"&UserName={self.username}&ClientIp={self.client_ip}&Command={command}"
        )
        for key, value in params.items():
            base_url += f"&{key}={value}"
        return base_url

    def _make_api_request(self, url: str) -> Dict:
        """
        Make request to Namecheap API and convert XML response to dict.
        Raises HTTPException on error.
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Convert XML to dict
            data = xmltodict.parse(response.text)

            # Check for API errors
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
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to Namecheap API: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )

    def get_domain_info(self, sld: str, tld: str, username: str) -> DomainInfoResponse:
        """
        Retrieves comprehensive information about a domain.

        Args:
            sld: Second-level domain (e.g., 'example' in example.com)
            tld: Top-level domain (e.g., 'com' in example.com)
            username: Username of the requesting user

        Returns:
            DomainInfoResponse with domain details
        """
        url = self._build_api_url(
            "namecheap.domains.getInfo",
            DomainName=f"{sld}.{tld}"
        )

        data = self._make_api_request(url)

        # Extract domain info from response
        cmd_response = data['ApiResponse']['CommandResponse']
        domain_info = cmd_response['DomainGetInfoResult']

        # Parse dates
        created_date = self._parse_date(domain_info.get('@CreatedDate'))
        expires_date = self._parse_date(domain_info.get('@ExpiredDate'))

        # Extract nameservers
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
        Retrieves all DNS records for a domain.

        Args:
            sld: Second-level domain
            tld: Top-level domain

        Returns:
            List of DNSRecordResponse objects
        """
        url = self._build_api_url(
            "namecheap.domains.dns.getHosts",
            SLD=sld,
            TLD=tld
        )

        data = self._make_api_request(url)

        # Extract host records
        cmd_response = data['ApiResponse']['CommandResponse']
        hosts_data = cmd_response['DomainDNSGetHostsResult'].get('host', [])

        # Ensure hosts_data is a list
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
        Updates DNS records for a domain. This replaces ALL existing records.

        Args:
            sld: Second-level domain
            tld: Top-level domain
            records: List of DNS records to set

        Returns:
            Updated list of DNS records
        """
        if not records:
            raise HTTPException(
                status_code=400,
                detail="At least one DNS record is required"
            )

        # Build parameters for setHosts call
        params = {"SLD": sld, "TLD": tld}

        for idx, record in enumerate(records, start=1):
            params[f"HostName{idx}"] = record.hostname
            params[f"RecordType{idx}"] = record.record_type
            params[f"Address{idx}"] = record.address
            params[f"TTL{idx}"] = str(record.ttl)

            if record.record_type == "MX":
                params[f"MXPref{idx}"] = str(record.mx_pref)

        url = self._build_api_url("namecheap.domains.dns.setHosts", **params)
        self._make_api_request(url)

        # Return updated records
        return self.get_dns_records(sld, tld)

    def set_url_forwarding(self, sld: str, tld: str, target_url: str, forward_type: str = "permanent") -> Dict:
        """
        Sets up URL forwarding for a domain.

        Args:
            sld: Second-level domain
            tld: Top-level domain
            target_url: URL to forward to
            forward_type: 'permanent' (301) or 'temporary' (302)

        Returns:
            Success status dictionary
        """
        # Namecheap expects the subdomain for forwarding
        # Use '@' for root domain forwarding
        url = self._build_api_url(
            "namecheap.domains.dns.setHosts",
            SLD=sld,
            TLD=tld,
            HostName1="@",
            RecordType1="URL",
            Address1=target_url,
            TTL1="100"
        )

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
        Sets up basic hosting by configuring A and CNAME records.

        Args:
            sld: Second-level domain
            tld: Top-level domain
            custom_ip: Optional custom IP (uses default if not provided)

        Returns:
            Dictionary with success status and configured records
        """
        hosting_ip = custom_ip or self.default_hosting_ip

        # Standard hosting records
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
        Gets comprehensive status including info, DNS, and configuration.

        Args:
            sld: Second-level domain
            tld: Top-level domain
            username: Username of requesting user

        Returns:
            DomainStatusResponse with all domain details
        """
        domain_info = self.get_domain_info(sld, tld, username)
        dns_records = self.get_dns_records(sld, tld)

        # Check if domain is hosted (has A record for @)
        is_hosted = any(
            r.hostname == "@" and r.record_type == "A"
            for r in dns_records
        )

        # Check if domain is forwarding (has URL record)
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
        """Parse Namecheap date format to datetime object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%m/%d/%Y")
        except (ValueError, TypeError):
            return None