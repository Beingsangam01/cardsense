from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class SharedLimitGroup(Base):
    __tablename__ = "shared_limit_groups"

    id         = Column(Integer, primary_key=True, index=True)
    group_name = Column(String(100), nullable=False)
    total_limit = Column(Integer, nullable=False, default=0)
    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    cards = relationship("Card", back_populates="shared_group")