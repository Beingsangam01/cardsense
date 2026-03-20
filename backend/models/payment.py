from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=True)
    payment_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    payment_type = Column(String)    
    reference_number = Column(String)   
    notes = Column(Text)

    card = relationship("Card", back_populates="payments")
    statement = relationship("Statement", back_populates="payments")