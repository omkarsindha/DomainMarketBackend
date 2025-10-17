from celery import Celery
from celery.schedules import crontab
from database.connection import SessionLocal
from services.auction_service import AuctionService
from models.db_models import Auction, AuctionStatus
from datetime import datetime

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

        # Find all active auctions that have ended
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
                # We use the internal closing logic which doesn't require a username
                # since this is a system-triggered action.
                auction_service._system_close_auction(auction.id, db)
                print(f"Successfully closed auction {auction.id}.")
            except Exception as e:
                # Log the error but continue to the next auction
                print(f"Error closing auction {auction.id}: {str(e)}")

    finally:
        db.close()


# Define the schedule for the periodic task
celery_app.conf.beat_schedule = {
    'check-expired-auctions-every-minute': {
        'task': 'celery_worker.check_and_close_expired_auctions',
        'schedule': crontab(),  # This runs the task every minute
    },
}

celery_app.conf.timezone = 'UTC'