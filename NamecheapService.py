import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv


class NamecheapService:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # Initialize API credentials and settings
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

    def check_domains(self, domains):
        """Check availability of multiple domains and parse XML response."""
        if not domains:
            return {"error": "No domains provided"}

        url = self._build_api_url("namecheap.domains.check", DomainList=",".join(domains))

        try:
            response = self._make_api_request(url)
            root = ET.fromstring(response.text)
            namespace = {"nc": "http://api.namecheap.com/xml.response"}
            available_domains = []

            for domain in root.findall(".//nc:DomainCheckResult", namespace):
                name = domain.get("Domain")
                available = domain.get("Available") == "true"
                available_domains.append({"domain": name, "available": available})

            return {"domains": available_domains}

        except ET.ParseError:
            return {"error": "Failed to parse XML response", "raw_response": response.text}
        except Exception as e:
            return {"error": str(e)}

    def get_trending_tlds(self):
        """Fetches trending TLDs and their pricing."""
        try:
            tld_url = self._build_api_url("namecheap.domains.getTldList")
            tld_response = self._make_api_request(tld_url)
            # print("This is " + tld_response.text)

            root = ET.fromstring(tld_response.text)

            # Extract TLD names
            tlds = [tld.get("Name") for tld in root.findall(".//Tld")]
            if not tlds:
                return {"error": "No TLDs found"}

            # Fetch pricing information
            pricing_url = self._build_api_url("namecheap.domains.getPricing")
            pricing_response = self._make_api_request(pricing_url)
            pricing_root = ET.fromstring(pricing_response.text)

            # Extract prices for top 10 trending TLDs
            trending_tlds = []
            for tld in tlds[:10]:
                price_element = pricing_root.find(f".//Tld[@Name='{tld}']")
                if price_element is not None:
                    price = price_element.get("RegistrationPrice", "N/A")
                    trending_tlds.append({"tld": tld, "price": price})

            return trending_tlds

        except Exception as e:
            return {"error": str(e)}

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

    print("Checking DOmain availability...")
    print(domain_checker.check_domains(["google.com", "example.com", "test123.ca"]))

    print("Fetching trending TLDs...")
    print(domain_checker.get_trending_tlds())
    #
    # print("Registering a test domain...")
    # print(domain_checker.register_domain("exampletestdomain123.com"))
