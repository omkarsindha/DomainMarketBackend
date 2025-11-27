import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session
from models.db_models import Notification, UserDevice
from datetime import datetime
import os

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)


class NotificationService:

    def register_device(self, user_id: int, fcm_token: str, db: Session):
        """Saves a user's device token."""
        existing_device = db.query(UserDevice).filter(UserDevice.fcm_token == fcm_token).first()
        if existing_device:
            existing_device.user_id = user_id  # Update user if token exists (e.g. logout/login)
            existing_device.last_active = datetime.utcnow()
        else:
            new_device = UserDevice(user_id=user_id, fcm_token=fcm_token)
            db.add(new_device)
        db.commit()

    def send_notification(self, user_id: int, title: str, body: str, data: dict, db: Session):
        """
        1. Saves notification to DB.
        2. Sends Push Notification via Firebase.
        """
        # 1. Save to DB History
        db_notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            # You can map data['type'] to related_auction_id if needed
        )
        db.add(db_notification)
        db.commit()

        # 2. Get User's Devices
        devices = db.query(UserDevice).filter(UserDevice.user_id == user_id).all()
        if not devices:
            return  # No devices to push to

        tokens = [d.fcm_token for d in devices]

        # 3. Send via Firebase
        # MulticastMessage sends to multiple tokens at once
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data,  # Custom data payload (e.g., for deep linking: {"screen": "AuctionDetail", "id": "123"})
            tokens=tokens,
        )

        try:
            response = messaging.send_multicast(message)
            print(f"Sent notifications. Success: {response.success_count}, Fail: {response.failure_count}")
        except Exception as e:
            print(f"Error sending FCM: {str(e)}")