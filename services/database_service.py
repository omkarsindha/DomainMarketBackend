from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from database.connection import get_db
from models.db_models import User, UserDetails, Domain, Auction, Transaction, Listing, AuctionStatus, ListingStatus
from models.api_dto import DomainRegisterUserDetails

class DatabaseService:
    def get_user_domains(self, username: str, db: Session):
        """
        Fetch all domains owned by a user, including their auction and listing status.
        """
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return []
        # query domains and left join with active auctions and listings
        domains_with_status = db.query(
            Domain,
            Auction.id.isnot(None).label("is_auctioned"),
            Listing.id.isnot(None).label("is_listed")
        ).outerjoin(
            Auction, (Domain.id == Auction.domain_id) & (Auction.status == AuctionStatus.ACTIVE)
        ).outerjoin(
            Listing, (Domain.id == Listing.domain_id) & (Listing.status == ListingStatus.ACTIVE)
        ).filter(Domain.user_id == user.id).all()

        response = []
        for domain, is_auctioned, is_listed in domains_with_status:
            response.append({
                "id": domain.id,
                "domain_name": domain.domain_name,
                "price": domain.price,
                "bought_date": domain.bought_date,
                "expiry_date": domain.expiry_date,
                "is_auctioned": is_auctioned,
                "is_listed": is_listed,
            })

        return response

    def get_user_auctions(self, username: str, db: Session):
        """Fetch all domains owned by a user."""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return []  # Or raise HTTPException if user not found

        auctions = db.query(Auction).filter(Auction.seller_id == user.id).all()
        return auctions

    def get_user_transactions(self, username: str, db: Session):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return []
        transactions = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.transaction_date.desc()).all()
        return transactions

    def get_user_details(self, username: str, db):
        """Fetch user details based on the username."""
        user = db.query(User).filter(User.username == username).one()
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user.id).one()
        return user_details

    def get_user(self, username: str, db: Session):
        """
        Fetches a user and their email from the related details table efficiently.
        """
        user = db.query(User).filter(User.username == username).one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "username": user.username,
            "email": user.email
        }


    def create_or_update_user_details(self, username: str, user_details_dto: DomainRegisterUserDetails, db):
        """Create or update user details for a given username."""
        user = db.query(User).filter(User.username == username).one()
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user.id).first()

        if not user_details:
            user_details = UserDetails(user_id=user.id)

        formatted_phone = self._format_phone_number(user_details_dto.phone_number)
        user_details.phone_number = formatted_phone
        user_details.first_name = user_details_dto.first_name
        user_details.last_name = user_details_dto.last_name
        user_details.address = user_details_dto.address
        user_details.city = user_details_dto.city
        user_details.state = user_details_dto.state
        user_details.zip_code = user_details_dto.zip_code
        user_details.country = user_details_dto.country

        db.add(user_details)
        db.commit()
        db.refresh(user_details)
        return user_details

    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number to +NNN.NNNNNNNNNN format."""
        if not phone_number:
            return phone_number

        digits_only = ''.join(filter(str.isdigit, phone_number))

        if len(digits_only) < 10:
            return phone_number

        last_10 = digits_only[-10:]
        country_code = digits_only[:-10]

        if not country_code:
            country_code = "1"
        return f"+{country_code}.{last_10}"

if __name__ == "__main__":
    database_service = DatabaseService()
    db = next(get_db())
    details = database_service.get_user_details(username="omkar", db=db)
    print(details.email)
    print(details.first_name)


