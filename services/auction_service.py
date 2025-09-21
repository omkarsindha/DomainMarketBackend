from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models.db_models import User, Domain, Auction, Bid, AuctionStatus, TransactionType
from models.api_dto import AuctionCreateRequest, BidCreateRequest, AuctionResponse, BidResponse
from typing import List

from services.payment_service import PaymentService


class AuctionService:
    def create_auction(self, request: AuctionCreateRequest, username: str, db: Session):
        # Find the user who is creating the auction
        seller = db.query(User).filter(User.username == username).first()
        if not seller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")

        # Find the domain and verify ownership
        domain = db.query(Domain).filter(Domain.domain_name == request.domain_name).first()
        if not domain:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found.")

        if domain.user_id != seller.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this domain.")

        # Check if the domain is already in an auction
        existing_auction = db.query(Auction).filter(Auction.domain_id == domain.id,
                                                    Auction.status == AuctionStatus.ACTIVE).first()
        if existing_auction:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="This domain is already in an active auction.")

        # Create the new auction
        end_time = datetime.utcnow() + timedelta(days=request.duration_days)
        new_auction = Auction(
            domain_id=domain.id,
            seller_id=seller.id,
            start_price=request.start_price,
            end_time=end_time,
            status=AuctionStatus.ACTIVE
        )
        db.add(new_auction)
        db.commit()
        db.refresh(new_auction)
        return new_auction

    def place_bid(self, auction_id: int, request: BidCreateRequest, username: str, db: Session):
        # 1. Find the bidder and the auction
        bidder = db.query(User).filter(User.username == username).first()
        auction = db.query(Auction).get(auction_id)

        if not auction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found.")

        # 2. Validation checks
        if auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This auction is not active.")

        if auction.end_time < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This auction has already ended.")

        if auction.seller_id == bidder.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot bid on your own auction.")

        # 3. Check if bid amount is valid
        highest_bid = db.query(Bid).filter(Bid.auction_id == auction_id).order_by(Bid.bid_amount.desc()).first()

        min_bid_amount = highest_bid.bid_amount if highest_bid else auction.start_price

        if request.amount <= min_bid_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Your bid must be higher than the current highest bid of ${min_bid_amount}.")

        # 4. Create and save the new bid
        new_bid = Bid(
            auction_id=auction.id,
            bidder_id=bidder.id,
            bid_amount=request.amount
        )
        db.add(new_bid)
        db.commit()
        db.refresh(auction)  # Refresh auction to show new bid
        return auction

    def get_auction_details(self, auction_id: int, db: Session):
        auction = db.query(Auction).get(auction_id)
        if not auction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found.")
        return self._format_auction_response(auction)

    def get_active_auctions(self, db: Session):
        auctions = db.query(Auction).filter(Auction.status == AuctionStatus.ACTIVE).all()
        return [self._format_auction_response(auc) for auc in auctions]

    def close_auction(self, auction_id: int, username: str, db: Session):
        # 1. Find the auction and the user trying to close it
        auction = db.query(Auction).get(auction_id)
        user = db.query(User).filter(User.username == username).first()

        if not auction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found.")

        # 2. Only the seller can close the auction
        if auction.seller_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the seller can close this auction.")

        if auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction is not active.")

        # 3. Find the winning bid
        winning_bid = db.query(Bid).filter(Bid.auction_id == auction_id).order_by(Bid.bid_amount.desc()).first()

        if winning_bid:
            # A winner exists, so we process the transfer and transactions
            auction.winner_id = winning_bid.bidder_id

            # --- A. Transfer domain ownership and update its details ---
            domain = db.query(Domain).get(auction.domain_id)
            domain.user_id = winning_bid.bidder_id
            domain.bought_date = datetime.utcnow()  # Set new acquisition date
            domain.price = winning_bid.bid_amount  # Update price to what the winner paid

            payment_service = PaymentService()

            # Transaction for the WINNER (Buyer)
            payment_service.create_transaction(
                user_id=winning_bid.bidder_id,
                domain_id=domain.id,
                auction_id=auction.id,
                transaction_type=TransactionType.AUCTION_WIN,
                amount=winning_bid.bid_amount,
                description=f"Won auction for domain {domain.domain_name}",
                domain_name_at_purchase=domain.domain_name,
                status="COMPLETED",
                db=db
            )

            # Transaction for the SELLER
            payment_service.create_transaction(
                user_id=auction.seller_id,
                domain_id=domain.id,
                auction_id=auction.id,
                transaction_type=TransactionType.AUCTION_SALE,  # Use the new type
                amount=winning_bid.bid_amount,
                description=f"Sold domain {domain.domain_name} in auction",
                domain_name_at_purchase=domain.domain_name,
                status="COMPLETED",
                db=db
            )

        # 4. Mark the auction as closed
        auction.status = AuctionStatus.CLOSED

        # 5. Commit all changes to the database at once
        db.commit()
        db.refresh(auction)

        return self._format_auction_response(auction)

    def _format_auction_response(self, auction: Auction):
        """Helper to format the response model consistently."""
        highest_bid = auction.bids[0].bid_amount if auction.bids else None

        return AuctionResponse(
            id=auction.id,
            domain_name=auction.domain.domain_name,
            seller_username=auction.seller.username,
            start_price=float(auction.start_price),
            current_highest_bid=float(highest_bid) if highest_bid else None,
            end_time=auction.end_time,
            status=auction.status.value,
            winner_username=auction.winner.username if auction.winner else None,
            bids=[BidResponse(
                bidder_username=bid.bidder.username,
                bid_amount=float(bid.bid_amount),
                created_at=bid.created_at
            ) for bid in auction.bids]
        )

    def get_auctions_by_seller(self, username: str, db: Session) -> List[AuctionResponse]:
        seller = db.query(User).filter(User.username == username).first()
        if not seller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller user not found.")

        auctions = db.query(Auction).filter(
            Auction.seller_id == seller.id
        ).all()
        return [self._format_auction_response(auc) for auc in auctions]

    def get_auctions_by_bidder(self, username: str, db: Session) -> List[AuctionResponse]:
        bidder_user = db.query(User).filter(User.username == username).first()
        if not bidder_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bidder user not found.")

        # Get auction IDs where this user has placed a bid
        bidded_auction_ids = db.query(Bid.auction_id).filter(Bid.bidder_id == bidder_user.id).distinct().all()
        bidded_auction_ids = [aid[0] for aid in bidded_auction_ids] # Extract IDs from tuples

        auctions = db.query(Auction).filter(
            Auction.id.in_(bidded_auction_ids)
        ).all()
        return [self._format_auction_response(auc) for auc in auctions]

    def get_auctions_won_by_user(self, username: str, db: Session) -> List[AuctionResponse]:
        winner_user = db.query(User).filter(User.username == username).first()
        if not winner_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Winner user not found.")

        auctions = db.query(Auction).filter(
            Auction.winner_id == winner_user.id,
            Auction.status == AuctionStatus.CLOSED
        ).all()
        return [self._format_auction_response(auc) for auc in auctions]