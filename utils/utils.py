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


if __name__ == "__main__":
    usd_value = 100
    cad_value = convert_usd_to_cad(usd_value)

    if cad_value is not None:
        print(f"{usd_value} USD is equal to {cad_value:.2f} CAD")
    else:
        print("Currency conversion failed.")
