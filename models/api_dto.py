from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal



class DomainRegisterUserDetails(BaseModel):
    phone_number: str
    first_name: str
    last_name: str
    address: str
    city: str
    state: str
    zip_code: str
    country: str

class DomainRegistrationRequest(BaseModel):
    domain: str
    years: int = 1

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class DomainsCheckRequest(BaseModel):
    domain: str

class PaymentRequest(BaseModel):
    domain: str
    price: float
    years: int = 1


class AuctionCreateRequest(BaseModel):
    domain_name: str
    start_price: float = Field(..., gt=0, description="The starting price for the auction.")
    duration_days: int = Field(..., gt=0, le=30, description="The duration of the auction in days.")

class BidCreateRequest(BaseModel):
    amount: float = Field(..., gt=0, description="The amount to bid.")

class BidResponse(BaseModel):
    bidder_username: str
    bid_amount: float
    created_at: datetime

    class Config:
        orm_mode = True

class AuctionResponse(BaseModel):
    id: int
    domain_name: str
    seller_username: str
    start_price: float
    current_highest_bid: Optional[float] = 0.0
    end_time: datetime
    status: str
    bids: List[BidResponse] = []
    winner_username: Optional[str] = None

    class Config:
        orm_mode = True


class ListingCreateRequest(BaseModel):
    domain_name: str
    price: float = Field(..., gt=0, description="The fixed price for the domain.")


class ListingResponse(BaseModel):
    id: int
    domain_name: str
    seller_username: str
    price: float
    created_at: datetime
    sold_at: Optional[datetime] = None
    status: str
    buyer_username: Optional[str] = None

    class Config:
        orm_mode = True


class SavePaymentRequest(BaseModel):
    username: str
    payment_method_id: str

class UserDomainResponse(BaseModel):
    id: int
    domain_name: str
    price: Decimal
    bought_date: datetime
    expiry_date: datetime

    class Config:
        orm_mode = True

class UserTransactionResponse(BaseModel):
    id: int
    transaction_type: str
    amount: Decimal
    currency: str
    transaction_date: datetime
    status: str
    description: Optional[str] = None
    domain_name_at_purchase: Optional[str] = None
    years_purchased: Optional[int] = None

    class Config:
        orm_mode = True

class UserMyDetailsResponse(BaseModel):
    username: str
    email: str

    class Config:
        from_attributes = True