from celery import Celery
from celery.schedules import crontab
from database.connection import SessionLocal
from services.auction_service import AuctionService
from models.db_models import Auction, AuctionStatus, Domain, Listing, ListingStatus, TransactionType
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload

from services.namecheap_service import NamecheapService
from services.notification_service import NotificationService
from services.payment_service import PaymentService
import stripe


# Configure Celery
celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


@celery_app.task
def check_and_close_expired_auctions():
    """
    A periodic task to find and close auctions whose end_time has passed.
    """
    db = SessionLocal()
    auction_service = AuctionService()
    try:
        print("Running scheduled task: Checking for expired auctions...")

        expired_auctions = db.query(Auction).filter(
            Auction.status == AuctionStatus.ACTIVE,
            Auction.end_time <= datetime.utcnow()
        ).all()

        if not expired_auctions:
            print("No expired auctions found.")
            return

        for auction in expired_auctions:
            print(f"Closing auction {auction.id} for domain '{auction.domain.domain_name}'...")
            try:
                auction_service._system_close_auction(auction.id, db)
                print(f"Successfully closed auction {auction.id}.")
            except Exception as e:
                print(f"Error closing auction {auction.id}: {str(e)}")

    finally:
        db.close()


@celery_app.task
def check_and_remove_expired_domains():
    """
    A periodic task to find expired domains. If an expired domain is part of
    an active auction/listing, that sale is cancelled, and the domain's user
    is disassociated (user_id is set to NULL).
    """
    db = SessionLocal()
    try:
        print("Running scheduled task: Checking for expired domains and associated sales...")

        # Find all expired domains and eagerly load their related auctions and listings.
        expired_domains = db.query(Domain).options(
            joinedload(Domain.auctions),
            joinedload(Domain.listings)
        ).filter(
            Domain.expiry_date <= datetime.utcnow(),
            Domain.user_id != None
        ).all()

        if not expired_domains:
            print("No expired domains found to process.")
            return

        domains_processed_count = 0
        for domain in expired_domains:
            # 1. Check for and cancel any active auctions for the expired domain.
            for auction in domain.auctions:
                if auction.status == AuctionStatus.ACTIVE:
                    print(f"Found active auction (ID: {auction.id}) for expired domain '{domain.domain_name}'. Cancelling auction.")
                    auction.status = AuctionStatus.CANCELLED

            # 2. Check for and cancel any active listings for the expired domain.
            for listing in domain.listings:
                if listing.status == ListingStatus.ACTIVE:
                    print(f"Found active listing (ID: {listing.id}) for expired domain '{domain.domain_name}'. Cancelling listing.")
                    listing.status = ListingStatus.CANCELLED

            # 3. After handling sales, disassociate the user from the domain.
            print(f"Domain '{domain.domain_name}' (ID: {domain.id}) has expired. Disassociating from user (ID: {domain.user_id}).")
            domain.user_id = None
            domains_processed_count += 1

        # 4. Commit all the changes (status updates and user disassociation) to the database.
        db.commit()
        print(f"Successfully processed and made {domains_processed_count} expired domains userless.")

    except Exception as e:
        print(f"An error occurred while processing expired domains: {str(e)}")
        db.rollback()
    finally:
        db.close()


@celery_app.task
def check_and_renew_expiring_domains():
    """
    Scheduled task to auto-renew domains.
    Runs daily. Checks for domains expiring in the next 24-48 hours.
    """
    db = SessionLocal()
    namecheap_service = NamecheapService()
    payment_service = PaymentService()

    try:
        print("Running scheduled task: Auto-renewing domains...")

        # Window: Expiring between tomorrow and day after tomorrow
        # (We run this daily, so we catch them 1 day before expiry)
        now = datetime.utcnow()
        window_start = now
        window_end = now + timedelta(days=2)

        # Find domains that are enabled for auto-renew and expiring soon
        expiring_domains = db.query(Domain).filter(
            Domain.auto_renew_enabled == True,
            Domain.expiry_date >= window_start,
            Domain.expiry_date <= window_end
        ).all()

        if not expiring_domains:
            print("No domains due for auto-renewal.")
            return

        for domain in expiring_domains:
            print(f"Processing auto-renewal for {domain.domain_name}...")

            user = domain.user
            if not user or not user.stripe_customer_id or not user.stripe_payment_method_id:
                print(f"Skipping {domain.domain_name}: User has no payment method.")
                # Optional: Send email to user saying renewal failed due to missing card
                continue

            try:
                # 1. Get Current Price (Assuming standard domain, 1 year)
                tld = domain.domain_name.split('.')[-1]
                price_info = namecheap_service.get_tld_price(tld)

                if "error" in price_info:
                    print(f"Skipping {domain.domain_name}: Could not fetch price.")
                    continue

                renewal_price = float(price_info["price"])

                # 2. Charge the User via Stripe
                print(f"Charging user {user.username} ${renewal_price} CAD...")
                payment_response = payment_service.create_and_confirm_payment(
                    amount=int(renewal_price * 100),  # Convert to cents
                    customer_id=user.stripe_customer_id,
                    payment_method_id=user.stripe_payment_method_id
                )

                if "error" in payment_response or payment_response.get("status") != "succeeded":
                    print(f"Payment failed for {domain.domain_name}: {payment_response.get('error')}")
                    continue

                # 3. Call Namecheap Renew API
                renew_result = namecheap_service.renew_domain(
                    domain_name=domain.domain_name,
                    years=1
                )

                if renew_result.get("success"):
                    # 4. Success: Update DB and Log Transaction
                    new_expiry = renew_result.get("new_expiry_date")

                    # Fallback if API didn't return date: add 1 year to current expiry
                    if not new_expiry:
                        new_expiry = domain.expiry_date + timedelta(days=365)

                    domain.expiry_date = new_expiry

                    # Log Transaction
                    payment_service.create_transaction(
                        user_id=user.id,
                        domain_id=domain.id,
                        transaction_type=TransactionType.DOMAIN_RENEWAL,
                        amount=renewal_price,
                        description=f"Auto-renewal for {domain.domain_name}",
                        domain_name_at_purchase=domain.domain_name,
                        years_purchased=1,
                        status="COMPLETED",
                        db=db
                    )

                    db.commit()
                    print(f"Successfully renewed {domain.domain_name}. New expiry: {new_expiry}")

                else:
                    # 5. Failure: Refund the user
                    print(f"Namecheap renewal failed for {domain.domain_name}. Issuing refund...")
                    payment_service._issue_refund(payment_response.get("payment_intent_id"))
                    # Optional: Log failed transaction

            except Exception as e:
                print(f"Exception processing {domain.domain_name}: {str(e)}")
                db.rollback()

    finally:
        db.close()


@celery_app.task
def send_push_notification_task(user_id: int, title: str, body: str, data: dict = None):
    """
    Async task to send notifications.
    """
    db = SessionLocal()
    service = NotificationService()
    try:
        # Ensure data is a dict of strings (Firebase requirement)
        if data:
            data = {k: str(v) for k, v in data.items()}

        service.send_notification(user_id, title, body, data or {}, db)
    finally:
        db.close()


celery_app.conf.beat_schedule = {
    'check-expired-auctions-every-minute': {
        'task': 'celery_worker.check_and_close_expired_auctions',
        'schedule': crontab(),  # Runs every minute
    },

    'check-expired-domains-every-10-minutes': {
        'task': 'celery_worker.check_and_remove_expired_domains',
        'schedule': crontab(minute='*/10'), # Runs every 10 minutes
    },

    'auto-renew-domains-daily': {
        'task': 'celery_worker.check_and_renew_expiring_domains',
        'schedule': crontab(hour=0, minute=0),  # Runs once a day at midnight
    },
}

celery_app.conf.timezone = 'UTC'

