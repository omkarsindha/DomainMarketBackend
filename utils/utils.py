import requests


def convert_usd_to_cad(usd_amount):
    """Converts USD to CAD using exchange rate API."""
    url = "https://v6.exchangerate-api.com/v6/6cdeb5d9db93fcb735409cb5/latest/USD"

    try:
        response = requests.get(url)
        data = response.json()

        if data["result"] == "success":
            exchange_rate = data["conversion_rates"]["CAD"]
            cad_amount = usd_amount * exchange_rate
            return round(cad_amount, 2)
        else:
            print("Error fetching exchange rates.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None

def generate_similar_domains(base_name):
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

if __name__ == "__main__":
    usd_value = 100
    cad_value = convert_usd_to_cad(usd_value)

    if cad_value is not None:
        print(f"{usd_value} USD is equal to {cad_value:.2f} CAD")
    else:
        print("Currency conversion failed.")
