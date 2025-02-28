import os
import requests
import xml.etree.ElementTree as ET
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_USER = os.getenv("API_USER")
API_KEY = os.getenv("API_KEY")
USERNAME = os.getenv("NAMEOFUSER")
CLIENT_IP = os.getenv("CLIENT_IP")
API_URL = "https://api.sandbox.namecheap.com/xml.response"

print(USERNAME)

def get_hardcoded_available_domains():
    random_domains = [
        "mynewcooldomain123.com",
        "techtrendsxyz.com",
        "futureappdev.net",
        "randomstartupidea.org",
        "mycustomsite789.info"
    ]

    domain_string = ",".join(random_domains)
    url = f"{API_URL}?ApiUser={API_USER}&ApiKey={API_KEY}&UserName={USERNAME}&Command=namecheap.domains.check&ClientIp={CLIENT_IP}&DomainList={domain_string}"

    response = requests.get(url)

    if response.status_code != 200:
        return json.dumps({"error": "Failed to fetch response from Namecheap API"})

    available_domains = []
    print(response.text)
    # Parse XML response with namespace handling
    root = ET.fromstring(response.text)
    namespace = {"nc": "http://api.namecheap.com/xml.response"}

    for domain in root.findall(".//nc:DomainCheckResult", namespace):
        name = domain.get("Domain")
        available = domain.get("Available") == "true"
        available_domains.append({"domain": name, "available": available})

    return json.dumps({"domains": available_domains}, indent=4)


# Example usage
json_result = get_hardcoded_available_domains()
print(json_result)
