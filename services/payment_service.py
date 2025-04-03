import os
import stripe
import dotenv
from services.namecheap_service import NamecheapService

dotenv.load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class PaymentService:
    def __init__(self):
        self.namecheap = NamecheapService()

    def payment_for_domain(self, domain: str):
        """Process payment for a domain by receiving only the domain name."""
        domain_tld = domain.split('.')[-1]  # Extract TLD
        domain_price = self.namecheap.get_tld_price(domain_tld).get('price', 0)

        if domain_price <= 0:
            return {"error": "Invalid domain price"}

        amount_in_cents = int(domain_price * 100)  # Convert to cents

        # Use the test token for the payment method
        payment_method = self.create_payment_method()  # Using test token
        if "error" in payment_method:
            return payment_method  # Return error if card creation fails

        # Create and confirm payment intent using the payment method
        return self.create_and_confirm_payment(amount_in_cents, payment_method["id"])

    def create_payment_method(self):
        """Use Stripe's predefined test token (tok_visa) for testing."""
        try:
            # Use the test token 'tok_visa' for testing purposes
            payment_method = stripe.PaymentMethod.create(
                type="card",
                card={"token": "tok_visa"}  # Token for testing purposes
            )
            print("Created Payment Method ID:", payment_method.id)  # Print to console
            return {"id": payment_method.id}
        except stripe.error.StripeError as e:
            return {"error": str(e)}

    def create_and_confirm_payment(self, amount: int, payment_method_id: str, currency: str = "cad"):
        """Create and confirm a payment intent using a payment method."""
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                payment_method=payment_method_id,
                confirm=True,  # Automatically confirm payment
            )
            return {"status": intent.status, "client_secret": intent.client_secret}
        except stripe.error.StripeError as e:
            return {"error": str(e)}
