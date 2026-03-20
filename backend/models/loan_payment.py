from sqlalchemy import (
    Column, Integer, Numeric, Date,
    String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class LoanPayment(Base):
    __tablename__ = "loan_payments"

    id                  = Column(Integer, primary_key=True, index=True)
    loan_id             = Column(
        Integer, ForeignKey("loans.id"), nullable=False
    )
    payment_date        = Column(Date, nullable=False)
    amount_paid         = Column(Numeric(10, 2), nullable=False)
    principal_component = Column(Numeric(10, 2), default=0)
    interest_component  = Column(Numeric(10, 2), default=0)
    reference_number    = Column(String(100), nullable=True)
    notes               = Column(Text, nullable=True)
    created_at          = Column(DateTime, server_default=func.now())

    loan = relationship("Loan", back_populates="payments")