from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint, Text
from sqlalchemy.sql import func
from .database import Base


class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    __table_args__ = (UniqueConstraint('user_id', 'event_type', name='uq_user_event_type'),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    email = Column(String, nullable=False)
    push_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    event_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class SentNotification(Base):
    __tablename__ = "sent_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    event_type = Column(String, index=True)
    event_id = Column(String, index=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now()) 