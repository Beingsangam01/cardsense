from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey, Text, Time
from sqlalchemy.orm import relationship
from .base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    transaction_date = Column(Date, nullable=False)
    transaction_time = Column(Time, nullable=True)      
    merchant = Column(String)
    description = Column(Text)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String)
    category = Column(String)
    is_emi = Column(String, default="no")
    is_subscription = Column(String, default="no")
    user_note     = Column(Text, nullable=True)       
    user_category = Column(String(100), nullable=True) 

    statement = relationship("Statement", back_populates="transactions")