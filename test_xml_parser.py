import os
import requests
import xml.etree.ElementTree as ET
import json
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

    def check_domains(self, domains):
        """
        Check availability of multiple domains.

        Args:
            domains (list): List of domain names to check

        Returns:
            str: JSON string with domain availability information
        """
        if not domains:
            return json.dumps({"error": "No domains provided"})

        domain_string = ",".join(domains)
        url = (f"{self.api_url}?ApiUser={self.api_user}&ApiKey={self.api_key}"
               f"&UserName={self.username}&Command=namecheap.domains.check"
               f"&ClientIp={self.client_ip}&DomainList={domain_string}")

        try:
            response = self._make_api_request(url)
            return self._parse_domain_check_response(response)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def check_hardcoded_domains(self):
        """
        Check availability of hardcoded test domains.

        Returns:
            str: JSON string with domain availability information
        """
        random_domains = [
            "mynewcooldomain123.com",
            "techtrendsxyz.com",
            "futureappdev.net",
            "randomstartupidea.org",
            "mycustomsite789.info"
        ]

        return self.check_domains(random_domains)

    def _make_api_request(self, url):
        """
        Make request to Namecheap API.

        Args:
            url (str): The full API URL with parameters

        Returns:
            requests.Response: The API response

        Raises:
            Exception: If API request fails
        """
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch response from Namecheap API. Status code: {response.status_code}")

        return response

    def _parse_domain_check_response(self, response):
        """
        Parse XML response from domain check API.

        Args:
            response (requests.Response): The API response

        Returns:
            str: JSON string with parsed domain availability information
        """
        available_domains = []

        # Parse XML response with namespace handling
        try:
            root = ET.fromstring(response.text)
            namespace = {"nc": "http://api.namecheap.com/xml.response"}

            for domain in root.findall(".//nc:DomainCheckResult", namespace):
                name = domain.get("Domain")
                available = domain.get("Available") == "true"
                available_domains.append({"domain": name, "available": available})

            return json.dumps({"domains": available_domains}, indent=4)
        except ET.ParseError:
            return json.dumps({"error": "Failed to parse XML response", "raw_response": response.text})


# Example usage
if __name__ == "__main__":
    domain_checker = NamecheapService()

    json_result = domain_checker.check_hardcoded_domains()
    print(json_result)

    # Alternatively, check custom domains
    # custom_domains = ["example1.com", "example2.org"]
    # json_result = domain_checker.check_domains(custom_domains)
    # print(json_result)