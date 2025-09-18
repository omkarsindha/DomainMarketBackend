from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from models.db_models import User, Auction, Bid, AutoBid, AuctionStatus
from models.api_dto import AutoBidCreateRequest, AutoBidResponse, BidCreateRequest
from typing import List, Optional


class AutoBidService:
    def create_auto_bid(self, auction_id: int, request: AutoBidCreateRequest, username: str, db: Session):
        # Find the bidder and the auction
        bidder = db.query(User).filter(User.username == username).first()
        auction = db.query(Auction).get(auction_id)

        if not auction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found.")

        if not bidder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # Validation checks
        if auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This auction is not active.")

        if auction.end_time < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This auction has already ended.")

        if auction.seller_id == bidder.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You cannot set auto-bid on your own auction.")

        # Check if user already has an active auto-bid for this auction
        existing_auto_bid = db.query(AutoBid).filter(
            AutoBid.auction_id == auction_id,
            AutoBid.bidder_id == bidder.id,
            AutoBid.is_active == True
        ).first()

        if existing_auto_bid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active auto-bid for this auction. Update or deactivate it first."
            )

        # Validate max amount is reasonable
        current_highest_bid = db.query(Bid).filter(Bid.auction_id == auction_id).order_by(Bid.bid_amount.desc()).first()
        min_required = current_highest_bid.bid_amount if current_highest_bid else auction.start_price

        if request.max_amount <= min_required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Auto-bid max amount must be higher than the current highest bid of ${min_required}."
            )

        # Create the auto-bid
        new_auto_bid = AutoBid(
            auction_id=auction_id,
            bidder_id=bidder.id,
            max_amount=request.max_amount,
            increment=request.increment,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_auto_bid)
        db.commit()
        db.refresh(new_auto_bid)

        # IMMEDIATELY process auto-bids to see if this auto-bid should trigger
        try:
            self.process_auto_bids_on_creation(auction_id, db)
        except Exception as e:
            print(f"Error processing auto-bids on creation: {e}")

        return self._format_auto_bid_response(new_auto_bid)

    def update_auto_bid(self, auto_bid_id: int, request: AutoBidCreateRequest, username: str, db: Session):
        # Find the auto-bid and verify ownership
        auto_bid = db.query(AutoBid).get(auto_bid_id)
        user = db.query(User).filter(User.username == username).first()

        if not auto_bid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auto-bid not found.")

        if auto_bid.bidder_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own auto-bids.")

        if not auto_bid.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update inactive auto-bid.")

        # Check if auction is still active
        if auto_bid.auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Cannot update auto-bid for inactive auction.")

        # Update the auto-bid
        auto_bid.max_amount = request.max_amount
        auto_bid.increment = request.increment
        auto_bid.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(auto_bid)

        return self._format_auto_bid_response(auto_bid)

    def deactivate_auto_bid(self, auto_bid_id: int, username: str, db: Session):
        auto_bid = db.query(AutoBid).get(auto_bid_id)
        user = db.query(User).filter(User.username == username).first()

        if not auto_bid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auto-bid not found.")

        if auto_bid.bidder_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can only deactivate your own auto-bids.")

        auto_bid.is_active = False
        auto_bid.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(auto_bid)

        return self._format_auto_bid_response(auto_bid)

    def get_user_auto_bids(self, username: str, db: Session) -> List[AutoBidResponse]:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        auto_bids = db.query(AutoBid).filter(AutoBid.bidder_id == user.id).all()
        return [self._format_auto_bid_response(ab) for ab in auto_bids]

    def get_auction_auto_bids(self, auction_id: int, db: Session) -> List[AutoBidResponse]:
        """Get all active auto-bids for a specific auction (admin/seller use)"""
        auction = db.query(Auction).get(auction_id)
        if not auction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found.")

        auto_bids = db.query(AutoBid).filter(
            AutoBid.auction_id == auction_id,
            AutoBid.is_active == True
        ).all()
        return [self._format_auto_bid_response(ab) for ab in auto_bids]

    def process_auto_bids_on_creation(self, auction_id: int, db: Session):
        """
        Process auto-bids when a new auto-bid is created.
        This checks if the new auto-bid should immediately place a bid.
        """
        # Get current highest bid
        current_highest_bid = db.query(Bid).filter(Bid.auction_id == auction_id).order_by(Bid.bid_amount.desc()).first()
        current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else 0

        # Get all active auto-bids for this auction, ordered by max amount descending
        auto_bids = db.query(AutoBid).filter(
            AutoBid.auction_id == auction_id,
            AutoBid.is_active == True
        ).order_by(AutoBid.max_amount.desc()).all()

        self._execute_auto_bids(auction_id, current_highest_amount, auto_bids, db)

    def process_auto_bids(self, auction_id: int, new_bid_amount: float, new_bidder_id: int, db: Session):
        """
        Process auto-bids after a new manual bid is placed.
        This should be called by the AuctionService after a successful manual bid.
        """
        # Get all active auto-bids for this auction, excluding the bidder who just placed the manual bid
        auto_bids = db.query(AutoBid).filter(
            AutoBid.auction_id == auction_id,
            AutoBid.is_active == True,
            AutoBid.bidder_id != new_bidder_id
        ).order_by(AutoBid.max_amount.desc()).all()

        return self._execute_auto_bids(auction_id, new_bid_amount, auto_bids, db)

    def _execute_auto_bids(self, auction_id: int, current_highest_amount: float, auto_bids: List[AutoBid], db: Session):
        """
        Execute auto-bids based on current highest amount and available auto-bids.
        """
        print("reached execute auto-bids")
        auction = db.query(Auction).get(auction_id)
        if auction.status != AuctionStatus.ACTIVE or auction.end_time < datetime.utcnow():
            return current_highest_amount

        # Process auto-bids in order of highest max_amount first
        for auto_bid in auto_bids:
            # Check if this auto-bid can still bid
            if auto_bid.max_amount <= current_highest_amount:
                continue

            # Calculate the next bid amount
            next_bid_amount = current_highest_amount + auto_bid.increment

            # Don't exceed the max amount
            if next_bid_amount > auto_bid.max_amount:
                next_bid_amount = auto_bid.max_amount

            # Ensure the bid is higher than current highest
            if next_bid_amount <= current_highest_amount:
                continue

            # Place the auto-bid
            try:
                auto_generated_bid = Bid(
                    auction_id=auction_id,
                    bidder_id=auto_bid.bidder_id,
                    bid_amount=next_bid_amount,
                    is_auto_bid=True,
                    created_at=datetime.utcnow()
                )
                db.add(auto_generated_bid)
                db.commit()

                current_highest_amount = next_bid_amount
                print(f"Auto-bid placed: ${next_bid_amount} by user {auto_bid.bidder_id}")

                # If we've reached the max amount for this auto-bid, deactivate it
                if next_bid_amount >= auto_bid.max_amount:
                    auto_bid.is_active = False
                    auto_bid.updated_at = datetime.utcnow()
                    db.commit()
                    print(f"Auto-bid {auto_bid.id} deactivated (reached max amount)")

            except Exception as e:
                db.rollback()
                print(f"Error placing auto-bid: {e}")
                continue

        return current_highest_amount

    def _format_auto_bid_response(self, auto_bid: AutoBid) -> AutoBidResponse:
        return AutoBidResponse(
            id=auto_bid.id,
            auction_id=auto_bid.auction_id,
            bidder_username=auto_bid.bidder.username,
            max_amount=auto_bid.max_amount,
            increment=auto_bid.increment,
            is_active=auto_bid.is_active
        )