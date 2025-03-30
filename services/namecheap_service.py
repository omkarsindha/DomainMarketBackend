import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from services.database_service import DatabaseService

database_service = DatabaseService()

class NamecheapService:
    def __init__(self):
        load_dotenv()

        self.api_user = os.getenv("API_USER")
        self.api_key = os.getenv("API_KEY")
        self.username = os.getenv("NAMEOFUSER")
        self.client_ip = os.getenv("CLIENT_IP")
        self.api_url = "https://api.sandbox.namecheap.com/xml.response"

    def _build_api_url(self, command, **params):
        """Builds a Namecheap API request URL with common parameters."""
        base_url = (f"{self.api_url}?ApiUser={self.api_user}&ApiKey={self.api_key}"
                    f"&UserName={self.username}&ClientIp={self.client_ip}&Command={command}")
        for key, value in params.items():
            base_url += f"&{key}={value}"
        return base_url

    def _make_api_request(self, url):
        """Make request to Namecheap API."""
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch response from Namecheap API. Status code: {response.status_code}")

        return response

    def check_domain_availability(self, domain: str):
        if "." in domain:
            base_name = domain.split('.')[0]
            original_domain = domain
        else:
            base_name = domain
            original_domain = f"{domain}.com"

        similar_domains = self._generate_similar_domains(base_name)
        all_domains_to_check = [original_domain] + similar_domains

        domain_results = self._check_domains_in_batches(all_domains_to_check)

        original_result = None
        suggestions = []

        for domain_name, domain_data in domain_results.items():
            if domain_data["available"]:
                regular_price = 10.99
                sale_price = 8.99
                sale_percentage = 18

                domain_info = {
                    "domain": domain_name,
                    "regular_price": regular_price,
                    "sale_price": sale_price,
                    "sale_percentage": sale_percentage
                }

                if domain_name.lower() == original_domain.lower():
                    original_result = domain_info
                else:
                    suggestions.append(domain_info)

        response = {"suggestions": suggestions}
        if original_result:
            response["domain"] = original_result

        return response

    def _check_domains_in_batches(self, domains, batch_size=5):
        """Check domain availability in batches to improve performance."""
        results = {}

        # Process domains in batches
        for i in range(0, len(domains), batch_size):
            batch = domains[i:i + batch_size]

            batch_results = self._check_domain_batch(batch)
            results.update(batch_results)

        return results

    def _check_domain_batch(self, domain_batch):
        """Check availability for a batch of domains."""
        url = self._build_api_url("namecheap.domains.check", DomainList=",".join(domain_batch))

        try:
            response = self._make_api_request(url)

            root = ET.fromstring(response.text)
            namespace = {"nc": "http://api.namecheap.com/xml.response"}

            batch_results = {}
            for domain_result in root.findall(".//nc:DomainCheckResult", namespace):
                domain_name = domain_result.get("Domain")
                available = domain_result.get("Available") == "true"

                batch_results[domain_name] = {
                    "available": available
                }

            return batch_results

        except ET.ParseError as e:
            print(f"[ERROR] Failed to parse XML response: {e}")
            # Return domains as unavailable in case of parse error
            return {domain: {"available": False} for domain in domain_batch}
        except Exception as e:
            print(f"[ERROR] Exception for batch: {e}")
            # Return domains as unavailable in case of error
            return {domain: {"available": False} for domain in domain_batch}

    def _generate_similar_domains(self, base_name):
        """Generate similar domain suggestions based on the base name."""
        tlds = ['com', 'net', 'org', 'io', 'co', 'app', 'dev', 'ai', 'xyz', 'tech']

        prefixes = ['my', 'get', 'the', 'try']
        suffixes = ['app', 'hub', 'pro', 'site', 'web', 'online']

        suggestions = []

        for tld in tlds:
            suggestions.append(f"{base_name}.{tld}")
        for prefix in prefixes:
            suggestions.append(f"{prefix}{base_name}.com")
        for suffix in suffixes:
            suggestions.append(f"{base_name}{suffix}.com")

        return list(set(suggestions))

    def get_trending_tlds(self):
        """Fetches trending TLDs and their pricing."""
        try:
            tld_url = self._build_api_url("namecheap.domains.getTldList")
            tld_response = self._make_api_request(tld_url)

            print("Getting TLD list...")

            root = ET.fromstring(tld_response.text)
            namespace = {"": "http://api.namecheap.com/xml.response"}

            tld_elements = root.findall(".//Tlds/Tld", namespace)

            if not tld_elements:
                return {"error": "No TLDs found in the response"}

            tlds = []
            for tld in tld_elements:
                tld_name = tld.get("Name")
                if tld_name:
                    tlds.append(tld_name)

            return tlds

        except ET.ParseError as e:
            return {"error": f"Failed to parse XML response: {str(e)}"}
        except Exception as e:
            return {"error": f"Error fetching TLDs: {str(e)}"}
   
    def get_trending_keywords(self):
        """
        Returns a list of trending keywords for domain names. This list can later be enhanced by fetching from external source
        """
        trending_keywords = [
            "ai","crypto","blockchain","startup","web3","nft","quantum","cybersecurity","greenenerygy","automation"
        ]
        return trending_keywords
    
    def get_trending_available_domains(self):
        """
        Finds trending available domains by checking domain availability for trending keywords.
        """
        trending_keywords = self.get_trending_keywords()
        available_domains = []

        for keyword in trending_keywords:
            domain_names = self._generate_similar_domains(keyword)
            for domain_name in domain_names:
                check_result = self.check_domain_availability(domain_name)

                if "domain" in check_result:  # Means it's available
                    available_domains.append({
                    "domain": check_result["domain"]["domain"],
                    "sale_price": check_result["domain"]["sale_price"],
                    "regular_price": check_result["domain"]["regular_price"]
                })

            # Stop if we have 5 trending domains
                if len(available_domains) >= 5:
                    break

        return available_domains


    def register_domain(self, domain: str, years: int, username, db):
        """
        Registers a domain using Namecheap API with only Registrant info.
        """
        user_details = database_service.get_user_details(username, db)
        params = {}
        for contact_type in ['Admin', 'Tech', 'AuxBilling', 'Registrant']:
            params[f'{contact_type}FirstName'] = user_details.first_name
            params[f'{contact_type}LastName'] = user_details.last_name
            params[f'{contact_type}Address1'] = user_details.address
            params[f'{contact_type}City'] = user_details.city
            params[f'{contact_type}StateProvince'] = user_details.state
            params[f'{contact_type}PostalCode'] = user_details.zip_code
            params[f'{contact_type}Country'] = user_details.country
            params[f'{contact_type}Phone'] = user_details.phone_number
            params[f'{contact_type}EmailAddress'] = user_details.email
        params["AddFreeWhoisguard"] = "yes"
        params["WGEnabled"] = "yes"
        params["DomainName"] = domain
        params["Years"] = years
        url = self._build_api_url("namecheap.domains.create", **params)
        try:
            response = self._make_api_request(url)
            root = ET.fromstring(response.text)

            # Check for API errors
            if root.find(".//Errors/Error") is not None:
                error_msg = root.find(".//Errors/Error").text
                return {"error": error_msg}

            return {"success": True, "message": "Domain registered successfully", "raw_response": response.text}

        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    domain_checker = NamecheapService()

    print("Checking Domain availability...")
    print(domain_checker.check_domain_availability("omkar.com"))

    # print("Fetching trending TLDs...")
    # print(domain_checker.get_trending_tlds())
    #
    # print("Registering a test domain...")
    # print(domain_checker.register_domain("exampletestdomain123.com"))
