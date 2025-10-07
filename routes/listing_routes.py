from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from services.auth_service import AuthService
from services.listing_service import ListingService
from models.api_dto import ListingCreateRequest, ListingResponse

router = APIRouter()
auth_service = AuthService()
listing_service = ListingService()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ListingResponse)
def create_listing(
    request: ListingCreateRequest,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Create a new fixed-price listing for a domain owned by the authenticated user.
    """
    listing = listing_service.create_listing(request, username, db)
    return listing_service._format_listing_response(listing)


@router.get("/", response_model=List[ListingResponse])
def get_active_listings(db: Session = Depends(get_db)):
    """
    Get a list of all currently active listings.
    """
    return listing_service.get_active_listings(db)


@router.get("/my-listings", response_model=List[ListingResponse])
def get_my_listings(
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Get a list of all listings created by the authenticated user.
    """
    return listing_service.get_listings_by_seller(username, db)


@router.get("/my-purchases", response_model=List[ListingResponse])
def get_my_purchases(
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Get a list of all domains purchased by the authenticated user via listings.
    """
    return listing_service.get_listings_purchased_by_user(username, db)


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing_details(
    listing_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a single listing.
    """
    return listing_service.get_listing_details(listing_id, db)


@router.post("/{listing_id}/purchase", response_model=ListingResponse)
def purchase_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Purchase a domain from an active listing.
    """
    return listing_service.purchase_listing(listing_id, username, db)


@router.delete("/{listing_id}", response_model=ListingResponse)
def cancel_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(auth_service.verify_token)
):
    """
    Cancel an active listing. Can only be done by the seller.
    """
    return listing_service.cancel_listing(listing_id, username, db)