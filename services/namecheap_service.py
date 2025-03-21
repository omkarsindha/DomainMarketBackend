import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv


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

            # pricing_url = self._build_api_url("namecheap.users.getPricing", ProductType="DOMAIN",
            #                                   ProductCategory="REGISTER")
            #
            # pricing_response = self._make_api_request(pricing_url)
            # print(pricing_response.text)
            # print("Getting pricing information...")
            # pricing_root = ET.fromstring(pricing_response.text)

            # trending_tlds = []
            # for tld in tlds:
            #     # Updated XPath to match the proper XML structure from the example response
            #     price_element = pricing_root.find(f".//ProductCategory[@Name='REGISTER']/Product[@Name='{tld}']/Price",
            #                                       namespace)
            #
            #     if price_element is not None:
            #         # Extract price information from the Price element
            #         price = price_element.get("Price", "N/A")
            #         trending_tlds.append({"tld": tld, "price": price})
            #     else:
            #         trending_tlds.append({"tld": tld, "price": "N/A"})

            return tlds

        except ET.ParseError as e:
            return {"error": f"Failed to parse XML response: {str(e)}"}
        except Exception as e:
            return {"error": f"Error fetching TLDs: {str(e)}"}


    # def register_domain(self, domain, years=1):
    #     """Registers a domain for a user."""
    #     url = self._build_api_url("namecheap.domains.create", DomainName=domain, Years=years)
    #
    #     try:
    #         response = self._make_api_request(url)
    #         root = ET.fromstring(response.text)
    #         namespace = {"nc": "http://api.namecheap.com/xml.response"}
    #
    #         success = root.find(".//nc:DomainCreateResult", namespace)
    #         if success is not None and success.get("Registered") == "true":
    #             return {"domain": domain, "status": "Registered successfully"}
    #         else:
    #             return {"domain": domain, "status": "Registration failed", "raw_response": response.text}
    #     except Exception as e:
    #         return {"error": str(e)}


if __name__ == "__main__":
    domain_checker = NamecheapService()

    print("Checking Domain availability...")
    print(domain_checker.check_domain_availability("omkar.com"))

    # print("Fetching trending TLDs...")
    # print(domain_checker.get_trending_tlds())
    #
    # print("Registering a test domain...")
    # print(domain_checker.register_domain("exampletestdomain123.com"))
