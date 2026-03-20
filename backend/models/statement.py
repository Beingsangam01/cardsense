from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base

class Statement(Base):
    __tablename__ = "statements"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    statement_month = Column(String)          
    statement_date = Column(Date)             
    statement_period_start = Column(Date, nullable=True)   
    statement_period_end = Column(Date, nullable=True)
    due_date = Column(Date, nullable=False)   
    total_amount = Column(Float, nullable=False)   
    minimum_due = Column(Float)               
    opening_balance = Column(Float, default=0)
    status = Column(String, default="Unpaid") 
    pdf_link = Column(Text)                   
    pdf_text = Column(Text)                   
    amount_paid = Column(Float, default=0)    
    outstanding = Column(Float)               
    gmail_message_id = Column(String, nullable=True)   

    card = relationship("Card", back_populates="statements")
    transactions = relationship("Transaction", back_populates="statement")
    payments = relationship("Payment", back_populates="statement")