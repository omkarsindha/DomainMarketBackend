import os
import dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Session
import stripe
from stripe import SetupIntent, PaymentMethod

from services.namecheap_service import NamecheapService
from models.db_models import Transaction, TransactionType, Domain, User
from models.api_dto import PaymentRequest

dotenv.load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class PaymentService:
    def __init__(self):

        self.namecheap = NamecheapService()
    def purchase_domain(self, payment_details: PaymentRequest, username: str, db: Session):
        """
        Pay for a domain using a saved payment method and register it if payment succeeds.
        """
        # Find username
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.stripe_customer_id or not user.stripe_payment_method_id:
            raise HTTPException(
                status_code=400,
                detail="A card is required to complete this purchase. Please add one to your account first."
            )

        total_price = payment_details.price
        amount_in_cents = int(total_price * 100)
        domain = payment_details.domain
        years = payment_details.years
        if total_price <= 0:
            return {"error": "Invalid domain price provided."}

        payment_response = self.create_and_confirm_payment(
            amount=amount_in_cents,
            customer_id=user.stripe_customer_id,
            payment_method_id=user.stripe_payment_method_id
        )
        payment_intent_id = payment_response.get("payment_intent_id")

        if "error" in payment_response:
            return {"error": f"Payment failed: {payment_response['error']}"}

        if payment_response.get("status") != "succeeded":
            return {"error": f"Payment not successful. Status: {payment_response.get('status')}"}

        #  If payment is successful then I register the domain
        registration_result = self.namecheap.register_domain(domain, years, total_price, username, db)
        print(registration_result)

        # If Registration unsuccessful
        if not registration_result.get("success"):
            self._issue_refund(payment_intent_id)

            raise HTTPException(
                status_code=502,
                detail={
                    "code": "DOMAIN_REGISTRATION_FAILED",
                    "message": "Your payment was successful, but the domain registration failed. Your payment has been automatically refunded.",
                    "provider_error": registration_result.get("error", "Unknown error from domain provider.")
                }
            )

        # create a transaction if everything was successful
        if registration_result.get("success"):
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
            "payment_status": payment_response.get("status"),
            "registration_result": registration_result
        }

    def create_and_confirm_payment(self, amount: int, customer_id: str, payment_method_id: str, currency: str = "cad"):
        """
        Creates and confirms a payment for a customer using their saved payment method.
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                payment_method=payment_method_id,
                off_session=True,
                confirm=True,
            )
            return {"status": intent.status, "payment_intent_id": intent.id}
        except stripe.error.CardError as e:
            return {"error": e.user_message or str(e)}
        except stripe.error.StripeError as e:
            return {"error": str(e)}

    def _issue_refund(self, payment_intent_id: str):
        """
        Issues a full refund for a given Payment Intent.
        """
        try:
            stripe.Refund.create(payment_intent=payment_intent_id)
            print(f"Successfully issued refund for Payment Intent: {payment_intent_id}")
        except stripe.error.StripeError as e:
            print(f"CRITICAL ERROR: Failed to issue refund for {payment_intent_id}. Error: {e}")


    def create_transaction(
            self,
            user_id: int,
            transaction_type: TransactionType,
            amount: float,
            description: str = None,
            domain_id: int = None,
            auction_id: int = None,
            listing_id: int = None,
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
            listing_id=listing_id,
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