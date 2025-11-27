import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import concurrent.futures
from datetime import datetime, timedelta
from services.database_service import DatabaseService
import utils.utils as utils
import models.db_models as models
database_service = DatabaseService()


class NamecheapService:
    def __init__(self):
        load_dotenv()

        self.api_user = os.getenv("API_USER")
        self.api_key = os.getenv("API_KEY")
        self.username = os.getenv("NAMEOFUSER")
        self.client_ip = os.getenv("CLIENT_IP")
        self.api_url = "https://api.sandbox.namecheap.com/xml.response"
        self.tld_price_cache = {}

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

        similar_domains = utils.generate_similar_domains(base_name)
        all_domains_to_check = [original_domain] + similar_domains

        batch_size = 2
        domain_results = {}
        tlds_to_check = set()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Split domains into batches
            batches = [all_domains_to_check[i:i + batch_size]
                       for i in range(0, len(all_domains_to_check), batch_size)]
            future_to_batch = {executor.submit(self._check_domain_batch, batch): batch
                               for batch in batches}

            for future in concurrent.futures.as_completed(future_to_batch):
                batch_results = future.result()
                domain_results.update(batch_results)

                for domain_name in batch_results:
                    tld = domain_name.split(".")[-1]
                    tlds_to_check.add(tld)

        tlds_needing_price = [tld for tld in tlds_to_check if tld not in self.tld_price_cache]
        if tlds_needing_price:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_tld = {executor.submit(self.get_tld_price, tld): tld
                                 for tld in tlds_needing_price}

                for future in concurrent.futures.as_completed(future_to_tld):
                    tld = future_to_tld[future]
                    try:
                        result = future.result()
                        if not isinstance(result, dict) or "error" not in result:  # If not an error dict
                            # Assuming get_tld_price now returns a dict with price and duration
                            self.tld_price_cache[tld] = result
                    except Exception as e:
                        print(f"Error fetching price for TLD {tld}: {e}")

        for domain_name, domain_data in domain_results.items():
            if not domain_data["is_premium"]:
                tld = domain_name.split(".")[-1]
                if tld in self.tld_price_cache:
                    price_info = self.tld_price_cache[tld]
                    if isinstance(price_info, dict):
                        # If price cache now stores a dict with price and duration
                        domain_data["price"] = price_info["price"]
                        domain_data["min_duration"] = price_info["min_duration"]
                    else:
                        # Backward compatibility if price cache still has just the price
                        domain_data["price"] = price_info
                        domain_data["min_duration"] = 1  # Default duration

        original_result = None
        suggestions = []

        for domain_name, domain_data in domain_results.items():
            if domain_data["available"]:
                domain_info = {
                    "domain": domain_name,
                    "price": domain_data.get("price"),
                    "min_duration": domain_data.get("min_duration", 1)  # Default to 1 if not found
                }

                if domain_name.lower() == original_domain.lower():
                    original_result = domain_info
                else:
                    suggestions.append(domain_info)

        response = {"suggestions": suggestions}
        if original_result:
            response["domain"] = original_result

        return response

    def _check_domain_batch(self, domain_batch):
        """Check availability for a batch of domains, including premium details."""
        url = self._build_api_url("namecheap.domains.check", DomainList=",".join(domain_batch))

        try:
            response = self._make_api_request(url)
            print(response.text)  # Debugging line, can be removed
            root = ET.fromstring(response.text)
            namespace = {"nc": "http://api.namecheap.com/xml.response"}

            batch_results = {}
            for domain_result in root.findall(".//nc:DomainCheckResult", namespace):
                domain_name = domain_result.get("Domain")
                available = domain_result.get("Available") == "true"
                is_premium = domain_result.get("IsPremiumName") == "true"

                if is_premium:
                    premium_price = float(domain_result.get("PremiumRegistrationPrice", 0))
                else:
                    premium_price = 0

                batch_results[domain_name] = {
                    "available": available,
                    "is_premium": is_premium,
                    "price": premium_price
                }

            return batch_results
        except Exception as e:
            print(f"Error checking domain batch: {e}")
            return {}

    def get_trending_tlds(self):
        """Fetches trending TLDs and their pricing."""
        tlds = ["ai", "com", "xyz", "io", "app", "dev", "store", "shop", "online", "co"]
        return tlds

    def get_trending_keywords(self):
        """
        Returns a list of trending keywords for domain names. This list can later be enhanced by fetching from external source
        """
        trending_keywords = [
            "ainewbie", "cryptobros", "blockchainbros", "startupfounders", "web3flukes", "nftbrokers", "quantumcomputingxyz", "cybersecuritygrumps", "greenerygods",
            "automation-automators"
        ]
        return trending_keywords

    def get_trending_available_domains(self):
        """
        Finds trending available domains by checking domain availability for trending keywords.
        This now uses the same reliable XML parsing as the main search function.
        """
        trending_keywords = self.get_trending_keywords()
        available_domains = []

        # 1. BATCHING: Combine all keywords into a single API call, just like the search.
        domain_names_to_check = [f"{keyword}.com" for keyword in trending_keywords]
        domain_list_str = ",".join(domain_names_to_check)

        url_availability = self._build_api_url("namecheap.domains.check", DomainList=domain_list_str)

        try:
            response_availability = self._make_api_request(url_availability)
            if response_availability.status_code != 200:
                print("Failed to get a valid response from Namecheap API.")
                return []  # Return empty if the API call failed

            # 2. PARSING XML: Use ElementTree to parse the response
            root = ET.fromstring(response_availability.text)
            namespace = {'ns': 'http://api.namecheap.com/xml.response'}

            for result in root.findall('.//ns:DomainCheckResult', namespace):
                # The critical check, identical to the logic in _check_domain_batch
                if result.get('Available').lower() == 'true':
                    domain_name = result.get('Domain')
                    price_info = self.get_tld_price("com")

                    if isinstance(price_info, dict) and "price" in price_info:
                        available_domains.append({
                            "domain": domain_name,
                            "price": price_info["price"]
                        })
            return available_domains

        except ET.ParseError as e:
            print(f"Error parsing XML from Namecheap: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred in get_trending_available_domains: {e}")
            return []

    def register_domain(self, domain: str, years: int, price, username, db):
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
            ns = {'ns': 'http://api.namecheap.com/xml.response'}

            # Check for API errors
            error = root.find(".//ns:Error", ns)
            if error is not None:
                return {"success": False, "error": error.text}

            # Check registration result
            result = root.find(".//ns:DomainCreateResult", ns)
            if result is not None and result.attrib.get("Registered") == "true":

                user = db.query(models.User).filter(models.User.username == username).first()
                if user:
                    # Create a new Domain record
                    current_time = datetime.utcnow()
                    expiration_date = current_time + timedelta(days=years * 365)
                    new_domain_record = models.Domain(
                        user_id=user.id,
                        domain_name=domain,
                        price=price,
                        bought_date=current_time,
                        expiry_date=expiration_date
                    )
                    db.add(new_domain_record)
                    db.commit()

                return {
                    "success": True,
                    "message": "Domain registered successfully",
                    "order_id": result.attrib.get("OrderID")
                }

            return {"success": False, "error": "Domain registration failed."}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_tld_price(self, tld):
        """Fetches the registration price and minimum duration of a given TLD"""
        # Return cached info if available
        if tld in self.tld_price_cache:
            return self.tld_price_cache[tld]

        url = self._build_api_url(
            "namecheap.users.getPricing",
            ProductType="DOMAIN",
            ProductCategory="REGISTER",
            ProductName=tld.upper()
        )

        try:
            response = self._make_api_request(url)
            ns = {'ns': 'http://api.namecheap.com/xml.response'}  # Namespace dictionary
            root = ET.fromstring(response.text)

            product_element = root.find(
                ".//ns:ProductCategory[@Name='register']/ns:Product[@Name='{0}']".format(tld.lower()),
                namespaces=ns)

            if product_element is not None:
                # Find the price element with the minimum duration
                price_elements = product_element.findall("ns:Price", namespaces=ns)
                if price_elements:
                    # Sort by Duration to find the minimum available
                    price_elements.sort(key=lambda x: int(x.get("Duration", "0")))
                    price_element = price_elements[0]  # Get the one with the lowest duration

                    price_str = price_element.get("Price")
                    duration_str = price_element.get("Duration")

                    if price_str is not None and duration_str is not None:
                        try:
                            price = float(price_str)
                            duration = int(duration_str)
                            converted_price = utils.convert_usd_to_cad(price)

                            # Store both price and duration in the cache
                            result = {
                                "price": converted_price,
                                "min_duration": duration,
                                "duration_type": price_element.get("DurationType", "YEAR")
                            }

                            self.tld_price_cache[tld] = result  # Cache the result
                            return result
                        except ValueError:
                            return {"error": f"Invalid format for price or duration: {price_str}, {duration_str}"}
                    return {"error": f"Price or duration attribute missing for {tld}"}
                else:
                    return {"error": f"No price elements found for {tld}"}
            else:
                return {"error": f"Product not found for {tld}"}

        except ET.ParseError as e:
            return {"error": f"Failed to parse XML response: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

    def renew_domain(self, domain_name: str, years: int, promotion_code: str = None, is_premium: bool = False,
                     premium_price: float = 0.0):
        """
        Renews a domain via Namecheap API.
        """
        params = {
            "DomainName": domain_name,
            "Years": years,
            "IsPremiumDomain": str(is_premium).lower()
        }

        if promotion_code:
            params["PromotionCode"] = promotion_code

        if is_premium and premium_price > 0:
            params["PremiumPrice"] = premium_price

        url = self._build_api_url("namecheap.domains.renew", **params)

        try:
            response = self._make_api_request(url)
            root = ET.fromstring(response.text)
            ns = {'ns': 'http://api.namecheap.com/xml.response'}

            # Check for API errors
            error = root.find(".//ns:Error", ns)
            if error is not None:
                return {"success": False, "error": error.text, "code": error.attrib.get("Number")}

            # Check renew result
            renew_result = root.find(".//ns:DomainRenewResult", ns)

            if renew_result is not None and renew_result.attrib.get("Renew") == "true":
                charged_amount = renew_result.attrib.get("ChargedAmount")
                order_id = renew_result.attrib.get("OrderID")
                transaction_id = renew_result.attrib.get("TransactionID")

                # Extract new expiration date from response details
                domain_details = renew_result.find("ns:DomainDetails", ns)
                expired_date_str = domain_details.find("ns:ExpiredDate",
                                                       ns).text if domain_details is not None else None

                new_expiry_date = None
                if expired_date_str:
                    try:
                        # Namecheap usually returns "MM/DD/YYYY HH:MM:SS AM/PM"
                        new_expiry_date = datetime.strptime(expired_date_str, "%m/%d/%Y %I:%M:%S %p")
                    except ValueError:
                        pass

                return {
                    "success": True,
                    "message": "Domain renewed successfully",
                    "charged_amount": charged_amount,
                    "order_id": order_id,
                    "transaction_id": transaction_id,
                    "new_expiry_date": new_expiry_date
                }

            return {"success": False, "error": "Domain renewal failed (API returned false)."}

        except Exception as e:
            return {"success": False, "error": f"Exception during renewal: {str(e)}"}

if __name__ == "__main__":
    domain_checker = NamecheapService()
    #print(domain_checker.get_tld_price("ai"))
    #print(domain_checker.check_domain_availability("omkar.com"))
    print(domain_checker.get_trending_available_domains())
    # print("Fetching trending TLDs...")
    # print(domain_checker.get_trending_tlds())
    #
    # print("Registering a test domain...")
    # print(domain_checker.register_domain("exampletestdomain123.com"))