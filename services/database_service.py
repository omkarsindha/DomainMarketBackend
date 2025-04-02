from sqlalchemy.orm import Session

from database.connection import get_db
from models.db_models import User, UserDetails
from models.api_dto import DomainRegisterUserDetails

class DatabaseService:
    def get_user_details(self, username: str, db):
        """Fetch user details based on the username."""
        user = db.query(User).filter(User.username == username).one()
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user.id).one()
        return user_details

    def create_or_update_user_details(self, username: str, user_details_dto: DomainRegisterUserDetails, db):
        """Create or update user details for a given username."""
        user = db.query(User).filter(User.username == username).one()
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user.id).first()

        if not user_details:
            user_details = UserDetails(user_id=user.id)

        user_details.phone_number = user_details_dto.phone_number
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

if __name__ == "__main__":
    database_service = DatabaseService()
    db = next(get_db())
    details = database_service.get_user_details(username="omkar", db=db)
    print(details.email)
    print(details.first_name)


