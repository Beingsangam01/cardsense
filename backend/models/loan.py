from sqlalchemy import Column, Integer, String, Numeric, Date, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Loan(Base):
    __tablename__ = "loans"

    id                    = Column(Integer, primary_key=True, index=True)
    lender_name           = Column(String(100), nullable=False)
    loan_type             = Column(String(50), nullable=False, default='Personal')
    loan_nickname         = Column(String(100), nullable=True)
    principal_amount      = Column(Numeric(12, 2), nullable=False)
    interest_rate         = Column(Numeric(5, 2), nullable=False)
    tenure_months         = Column(Integer, nullable=False)
    start_date            = Column(Date, nullable=False)
    emi_amount            = Column(Numeric(10, 2), nullable=False)
    emi_date              = Column(Integer, nullable=False, default=5)
    outstanding_principal = Column(Numeric(12, 2), nullable=False)
    total_paid            = Column(Numeric(12, 2), nullable=False, default=0)
    status                = Column(String(20), nullable=False, default='Active')
    notes                 = Column(Text, nullable=True)
    created_at            = Column(DateTime, server_default=func.now())

    # Relationship to payments
    payments = relationship(
        "LoanPayment",
        back_populates="loan",
        cascade="all, delete-orphan"
    )