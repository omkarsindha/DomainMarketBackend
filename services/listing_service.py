import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from models.db_models import User, Domain, Listing, ListingStatus, Auction, AuctionStatus, TransactionType
from models.api_dto import ListingCreateRequest, ListingResponse
from typing import List

from services.payment_service import PaymentService


class ListingService:
    def create_listing(self, request: ListingCreateRequest, username: str, db: Session):
        """Create a new fixed-price listing for a domain owned by the authenticated user."""
        # Find the user who is creating the listing
        seller = db.query(User).filter(User.username == username).first()
        if not seller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")

        # Find the domain and verify ownership
        domain = db.query(Domain).filter(Domain.domain_name == request.domain_name).first()
        if not domain:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found.")

        if domain.user_id != seller.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this domain.")

        # Check if the domain is already in an active auction
        existing_auction = db.query(Auction).filter(
            Auction.domain_id == domain.id,
            Auction.status == AuctionStatus.ACTIVE
        ).first()
        if existing_auction:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This domain is already in an active auction."
            )

        # Check if the domain is already listed
        existing_listing = db.query(Listing).filter(
            Listing.domain_id == domain.id,
            Listing.status == ListingStatus.ACTIVE
        ).first()
        if existing_listing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This domain is already listed for sale."
            )

        # Create the new listing
        new_listing = Listing(
            domain_id=domain.id,
            seller_id=seller.id,
            price=request.price,
            status=ListingStatus.ACTIVE
        )
        db.add(new_listing)
        db.commit()
        db.refresh(new_listing)
        return new_listing

    def get_active_listings(self, db: Session):
        """Get all active listings."""
        listings = db.query(Listing).filter(Listing.status == ListingStatus.ACTIVE).all()
        return [self._format_listing_response(listing) for listing in listings]

    def get_listing_details(self, listing_id: int, db: Session):
        """Get detailed information about a single listing."""
        listing = db.query(Listing).get(listing_id)
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
        return self._format_listing_response(listing)

    def get_listings_by_seller(self, username: str, db: Session) -> List[ListingResponse]:
        """Get all listings created by a specific seller."""
        seller = db.query(User).filter(User.username == username).first()
        if not seller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")

        listings = db.query(Listing).filter(Listing.seller_id == seller.id).all()
        return [self._format_listing_response(listing) for listing in listings]

    def get_listings_purchased_by_user(self, username: str, db: Session) -> List[ListingResponse]:
        """Get all listings purchased by a specific user."""
        buyer = db.query(User).filter(User.username == username).first()
        if not buyer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer not found.")

        listings = db.query(Listing).filter(
            Listing.buyer_id == buyer.id,
            Listing.status == ListingStatus.SOLD
        ).all()
        return [self._format_listing_response(listing) for listing in listings]

    def purchase_listing(self, listing_id: int, username: str, db: Session):
        """Purchase a domain from an active listing."""
        # Find the listing and buyer
        listing = db.query(Listing).get(listing_id)
        buyer = db.query(User).filter(User.username == username).first()

        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")

        if not buyer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer not found.")

        # Validation checks
        if listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This listing is not active.")

        if listing.seller_id == buyer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot purchase your own listing."
            )

        # Check if buyer has a saved payment method
        if not buyer.stripe_customer_id or not buyer.stripe_payment_method_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A card is required to complete this purchase. Please add one to your account first."
            )

        # Process payment with Stripe
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(listing.price * 100),  # Stripe expects cents
                currency="cad",
                customer=buyer.stripe_customer_id,
                payment_method=buyer.stripe_payment_method_id,
                off_session=True,
                confirm=True
            )
            payment_status = payment_intent.status
        except stripe.error.CardError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Payment failed: {e.user_message}"
            )

        # Transfer domain ownership
        domain = db.query(Domain).get(listing.domain_id)
        domain.user_id = buyer.id
        domain.bought_date = datetime.utcnow()
        domain.price = listing.price

        # Update listing
        listing.buyer_id = buyer.id
        listing.sold_at = datetime.utcnow()
        listing.status = ListingStatus.SOLD

        payment_service = PaymentService()

        # Create transaction for BUYER
        payment_service.create_transaction(
            user_id=buyer.id,
            domain_id=domain.id,
            listing_id=listing.id,
            transaction_type=TransactionType.LISTING_PURCHASE,
            amount=listing.price,
            description=f"Purchased domain {domain.domain_name} from listing",
            domain_name_at_purchase=domain.domain_name,
            status=payment_status.upper(),
            db=db
        )

        # Create transaction for SELLER
        payment_service.create_transaction(
            user_id=listing.seller_id,
            domain_id=domain.id,
            listing_id=listing.id,
            transaction_type=TransactionType.LISTING_SALE,
            amount=listing.price,
            description=f"Sold domain {domain.domain_name} via listing",
            domain_name_at_purchase=domain.domain_name,
            status=payment_status.upper(),
            db=db
        )

        # Commit all changes
        db.commit()
        db.refresh(listing)

        return self._format_listing_response(listing)

    def cancel_listing(self, listing_id: int, username: str, db: Session):
        """Cancel an active listing. Can only be done by the seller."""
        listing = db.query(Listing).get(listing_id)
        user = db.query(User).filter(User.username == username).first()

        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")

        # Only the seller can cancel the listing
        if listing.seller_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the seller can cancel this listing."
            )

        if listing.status != ListingStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listing is not active."
            )

        # Cancel the listing
        listing.status = ListingStatus.CANCELLED
        db.commit()
        db.refresh(listing)

        return self._format_listing_response(listing)

    def _format_listing_response(self, listing: Listing):
        """Helper to format the response model consistently."""
        return ListingResponse(
            id=listing.id,
            domain_name=listing.domain.domain_name,
            seller_username=listing.seller.username,
            price=float(listing.price),
            created_at=listing.created_at,
            sold_at=listing.sold_at,
            status=listing.status.value,
            buyer_username=listing.buyer.username if listing.buyer else None
        )