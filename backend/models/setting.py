from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from .base import Base

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())