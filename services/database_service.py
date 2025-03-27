from sqlalchemy.orm import Session
from models.db_models import User, UserDetails
from database.connection import get_db


class DatabaseService:
    def get_user_details(self, username: str, db: Session):
        """Fetch user details based on the username."""
        user = db.query(User).filter(User.username == username).one()
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user.id).one()
        return user_details

if __name__ == "__main__":
    database_service = DatabaseService()
    db = next(get_db())
    details = database_service.get_user_details(username="omkar", db=db)
    print(details.email)
    print(details.first_name)


