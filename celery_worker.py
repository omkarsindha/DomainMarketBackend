from celery import Celery
from celery.schedules import crontab
from database.connection import SessionLocal
from services.auction_service import AuctionService
from models.db_models import Auction, AuctionStatus, Domain, Listing, ListingStatus
from datetime import datetime
from sqlalchemy.orm import joinedload

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


celery_app.conf.beat_schedule = {
    'check-expired-auctions-every-minute': {
        'task': 'celery_worker.check_and_close_expired_auctions',
        'schedule': crontab(),  # Runs every minute
    },

    'check-expired-domains-every-10-minutes': {
        'task': 'celery_worker.check_and_remove_expired_domains',
        'schedule': crontab(minute='*/10'), # Runs every 10 minutes
    },
}

celery_app.conf.timezone = 'UTC'