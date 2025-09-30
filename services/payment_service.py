import os
import dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Session
import stripe
from stripe import SetupIntent, PaymentMethod

from services.namecheap_service import NamecheapService
from models.db_models import Transaction, TransactionType, Domain, User

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
        domain_price_whole = self.namecheap.get_tld_price(domain_tld)
        domain_price =domain_price_whole.get("price", 0)

        if domain_price <= 0:
            return {"error": "Invalid domain price"}

        total_price = domain_price * years
        amount_in_cents = int(total_price * 100)
        ################ Commented out the stripe payment to test
        # Step 2: Create and confirm payment
        # payment_response = self.create_and_confirm_payment(
        #     amount=amount_in_cents,
        #     payment_method_id=payment_token
        # )
        #
        # if "error" in payment_response:
        #     return {"error": f"Payment failed: {payment_response['error']}"}
        #
        # if payment_response.get("status") != "succeeded":
        #     return {"error": "Payment not successful"}

        # Step 3: Register domain after successful payment
        registration_result = self.namecheap.register_domain(domain, years, total_price, username, db)

        if registration_result.get("success"):
            user = db.query(User).filter(User.username == username).first()
            registered_domain_obj = db.query(Domain).filter(Domain.domain_name == domain,
                                                            Domain.user_id == user.id).first()
            if registered_domain_obj:
                self.create_transaction(
                    user_id=user.id,
                    domain_id=registered_domain_obj.id,
                    transaction_type=TransactionType.DOMAIN_REGISTRATION,
                    amount=total_price,
                    description=f"Registration of domain {domain} for {years} years.",
                    domain_name_at_purchase=domain,
                    years_purchased=years,
                    status="COMPLETED",
                    db=db
                )


        return {
            "payment_status": "succeeded",
            "registration_result": registration_result
        }
        # return {
        #     "payment_status": payment_response.get("status"),
        #     "registration_result": registration_result
        # }

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

    def create_transaction(
            self,
            user_id: int,
            transaction_type: TransactionType,
            amount: float,
            description: str = None,
            domain_id: int = None,
            auction_id: int = None,
            domain_name_at_purchase: str = None,
            years_purchased: int = None,
            status: str = "COMPLETED",
            db: Session = None
    ):
        """Creates a new transaction record."""
        new_transaction = Transaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            domain_id=domain_id,
            auction_id=auction_id,
            domain_name_at_purchase=domain_name_at_purchase,
            years_purchased=years_purchased,
            status=status
        )
        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)
        return new_transaction

    def create_setup_intent(self, username: str, db: Session):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(404, "User not found")
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.username)
            user.stripe_customer_id = customer.id
            db.commit()

            #####for testing purpose only #####
        pm = stripe.PaymentMethod.create(
            type="card",
            card={"token": "tok_visa"}
        )
        print(pm.id)


        setup_intent = stripe.SetupIntent.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"]
        )
        return {"client_secret": setup_intent.client_secret}

    def save_payment_method(self, username: str, payment_method_id: str, db: Session):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(404, "User not found")

        stripe.PaymentMethod.attach(payment_method_id, customer=user.stripe_customer_id)
        stripe.Customer.modify(user.stripe_customer_id, invoice_settings={"default_payment_method": payment_method_id})

        user.stripe_payment_method_id = payment_method_id
        db.commit()
        return {"message": "Payment method saved"}

    def get_payment_info(self, username: str, db: Session):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(404, "User not found")

        return {
            "username": user.username,
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_payment_method_id": user.stripe_payment_method_id,
        }

    def remove_payment_method(self, username: str, db: Session):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(404, "User not found")

        if not user.stripe_payment_method_id:
            raise HTTPException(400, "No payment method to remove")

        try:
            stripe.PaymentMethod.detach(user.stripe_payment_method_id)
            user.stripe_payment_method_id = None
            db.commit()

            return {"message": "Payment method removed successfully"}
        except stripe.error.StripeError as e:
            raise HTTPException(400, str(e))