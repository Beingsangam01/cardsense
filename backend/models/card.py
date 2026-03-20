from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Card(Base):
    __tablename__ = "cards"

    id                = Column(Integer, primary_key=True, index=True)
    bank_name         = Column(String, nullable=False)
    card_nickname     = Column(String, nullable=False)
    last_four_digits  = Column(String(4), nullable=False)
    statement_day     = Column(Integer)
    due_day           = Column(Integer)
    credit_limit      = Column(Integer)
    email_sender      = Column(String)
    pdf_password      = Column(String)
    is_active         = Column(String, default="yes")

    shared_group_id   = Column(
        Integer,
        ForeignKey("shared_limit_groups.id", ondelete="SET NULL"),
        nullable=True
    )

    shared_group = relationship(
        "SharedLimitGroup", back_populates="cards"
    )
    statements   = relationship("Statement", back_populates="card")
    payments     = relationship("Payment", back_populates="card")