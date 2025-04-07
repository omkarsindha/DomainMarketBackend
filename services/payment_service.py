import os

import dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Session
import stripe
from services.namecheap_service import NamecheapService


class PaymentService:
    def __init__(self):
        dotenv.load_dotenv()
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.namecheap = NamecheapService()

    def purchase_domain(self, domain: str, years: int, payment_token: str, username: str, db: Session):
        """
        Pay for a domain and register it if payment succeeds.
        """
        # Step 1: Get domain price
        domain_tld = domain.split('.')[-1]
        domain_price = self.namecheap.get_tld_price(domain_tld).get("price", 0)

        if domain_price <= 0:
            return {"error": "Invalid domain price"}

        total_price = domain_price * years
        amount_in_cents = int(total_price * 100)

        # Step 2: Create and confirm payment
        payment_response = self.create_and_confirm_payment(
            amount=amount_in_cents,
            payment_method_id=payment_token
        )

        if "error" in payment_response:
            return {"error": f"Payment failed: {payment_response['error']}"}

        if payment_response.get("status") != "succeeded":
            return {"error": "Payment not successful"}

        # Step 3: Register domain after successful payment
        registration_result = self.namecheap.register_domain(domain, years, username, db)

        return {
            "payment_status": payment_response.get("status"),
            "registration_result": registration_result
        }

    def create_and_confirm_payment(self, amount: int, payment_method_id: str, currency: str = "cad"):
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                payment_method=payment_method_id,
                confirm=True,
                return_url="http://localhost:8000/"
            )
            return {"status": intent.status, "client_secret": intent.client_secret}
        except stripe.error.StripeError as e:
            return {"error": str(e)}
