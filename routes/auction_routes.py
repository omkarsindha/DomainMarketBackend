from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from models.db_models import Auction
from services.auth_service import AuthService
from services.auction_service import AuctionService
from models.api_dto import AuctionCreateRequest, BidCreateRequest, AuctionResponse, AutoBidCreateRequest, \
    AutoBidResponse
from services.autobid_service import AutoBidService

router = APIRouter()
auth_service = AuthService()
auction_service = AuctionService()
auto_bid_service = AutoBidService()


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

@router.post("/{auction_id}/auto-bid", status_code=status.HTTP_201_CREATED, response_model=AutoBidResponse)
def create_auto_bid(
    auction_id: int,
    request: AutoBidCreateRequest,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Create an auto-bid for a specific auction.
    """
    return auto_bid_service.create_auto_bid(auction_id, request, username, db)

@router.put("/auto-bid/{auto_bid_id}", response_model=AutoBidResponse)
def update_auto_bid(
    auto_bid_id: int,
    request: AutoBidCreateRequest,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Update an existing auto-bid.
    """
    return auto_bid_service.update_auto_bid(auto_bid_id, request, username, db)

@router.delete("/auto-bid/{auto_bid_id}", response_model=AutoBidResponse)
def deactivate_auto_bid(
    auto_bid_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Deactivate an auto-bid.
    """
    return auto_bid_service.deactivate_auto_bid(auto_bid_id, username, db)

@router.get("/my-auto-bids", response_model=List[AutoBidResponse])
def get_my_auto_bids(
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Get all auto-bids for the authenticated user.
    """
    return auto_bid_service.get_user_auto_bids(username, db)

@router.get("/{auction_id}/auto-bids", response_model=List[AutoBidResponse])
def get_auction_auto_bids(
    auction_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Get all active auto-bids for a specific auction (for sellers/admins).
    """
    # You might want to add authorization to ensure only the seller or admin can see this
    return auto_bid_service.get_auction_auto_bids(auction_id, db)