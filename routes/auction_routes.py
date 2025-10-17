from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from stripe import PaymentMethodService

from database.connection import get_db
from services.auth_service import AuthService
from services.auction_service import AuctionService
from models.api_dto import AuctionCreateRequest, BidCreateRequest, AuctionResponse
from services.payment_service import PaymentService

router = APIRouter()
auth_service = AuthService()
auction_service = AuctionService()
payment_method_service = PaymentService()

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AuctionResponse)
def create_auction(
    request: AuctionCreateRequest,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Create a new auction for a domain owned by the authenticated user.
    """
    auction = auction_service.create_auction(request, username, db)
    return auction_service._format_auction_response(auction)


@router.get("/my-selling-auctions", response_model=List[AuctionResponse])
def get_my_selling_auctions(
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Get a list of auctions where the authenticated user is the seller.
    """
    return auction_service.get_auctions_by_seller(username, db)

@router.get("/my-bidding-auctions", response_model=List[AuctionResponse])
def get_my_bidding_auctions(
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Get a list of auctions where the authenticated user has placed a bid.
    """
    return auction_service.get_auctions_by_bidder(username, db)

@router.get("/my-won-auctions", response_model=List[AuctionResponse])
def get_my_won_auctions(
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Get a list of auctions won by the authenticated user.
    """
    return auction_service.get_auctions_won_by_user(username, db)

@router.get("/", response_model=List[AuctionResponse])
def get_active_auctions(db: Session = Depends(get_db)):
    """
    Get a list of all currently active auctions.
    """
    return auction_service.get_active_auctions(db)


@router.get("/{auction_id}", response_model=AuctionResponse)
def get_auction_details(
    auction_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a single auction, including all bids.
    """
    return auction_service.get_auction_details(auction_id, db)


@router.post("/{auction_id}/bids", response_model=AuctionResponse)
def place_bid(
    auction_id: int,
    request: BidCreateRequest,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Place a bid on an active auction.
    """
    auction = auction_service.place_bid(auction_id, request, username, db)
    return auction_service._format_auction_response(auction)


@router.post("/{auction_id}/close", response_model=AuctionResponse)
def close_auction(
    auction_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Close an auction. Can only be done by the seller.
    This will determine the winner and transfer the domain.
    """
    return auction_service.close_auction(auction_id, username, db)


@router.delete("/{auction_id}", response_model=AuctionResponse)
def cancel_auction(
    auction_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Cancel an active auction. Can only be done by the seller if no bids exist.
    """
    return auction_service.cancel_auction(auction_id, username, db)