"""
SQLAlchemy model representing application users.
"""

from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """
    User entity. Associated with uploaded media files.
    """

    __tablename__ = "User"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Relationships
    media_items = relationship("Media", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id})>"

