from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Enum
from sqlalchemy.orm import relationship
from database.connection import Base
from datetime import datetime
import enum

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, nullable=False)
    password_hash = Column(String)
    #for payments(Jeeni)
    stripe_customer_id = Column(String, nullable=True)
    stripe_payment_method_id = Column(String, nullable=True)

    # Relationships
    details = relationship("UserDetails", back_populates="user", uselist=False, cascade="all, delete-orphan")
    domains = relationship("Domain", back_populates="user")

class UserDetails(Base):
    __tablename__ = "user_details"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    country = Column(String, nullable=True)

    # Relationship with User
    user = relationship("User", back_populates="details")

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    domain_name = Column(String, unique=True, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    bought_date = Column(DateTime, nullable=False, default=datetime.utcnow) # Date of acquisition
    expiry_date = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User", back_populates="domains")
    auction = relationship("Auction", back_populates="domain", uselist=False)


class AuctionStatus(enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), unique=True, nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    start_price = Column(Numeric(10, 2), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(AuctionStatus), default=AuctionStatus.ACTIVE)

    domain = relationship("Domain", back_populates="auction")
    seller = relationship("User", foreign_keys='Auction.seller_id')
    winner = relationship("User", foreign_keys='Auction.winner_id')
    bids = relationship("Bid", back_populates="auction", cascade="all, delete-orphan", order_by="desc(Bid.bid_amount)")


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer, ForeignKey("auctions.id"), nullable=False)
    bidder_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    bid_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    auction = relationship("Auction", back_populates="bids")
    bidder = relationship("User")


class TransactionType(enum.Enum):
    DOMAIN_REGISTRATION = "DOMAIN_REGISTRATION"
    DOMAIN_RENEWAL = "DOMAIN_RENEWAL"
    DOMAIN_TRANSFER = "DOMAIN_TRANSFER"
    AUCTION_WIN = "AUCTION_WIN"
    AUCTION_SALE = "AUCTION_SALE"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=True) # Nullable if transaction is not domain specific
    auction_id = Column(Integer, ForeignKey("auctions.id"), nullable=True) # Nullable if not related to an auction

    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="CAD")
    transaction_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="COMPLETED")
    description = Column(String, nullable=True)

    domain_name_at_purchase = Column(String, nullable=True)
    years_purchased = Column(Integer, nullable=True)

    user = relationship("User", backref="transactions")
    domain = relationship("Domain", backref="transactions")
    auction = relationship("Auction", backref="transactions")
