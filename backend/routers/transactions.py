from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.base import get_db
from models.transaction import Transaction
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

#   Pydantic schema f
class TransactionUpdate(BaseModel):
    user_note:     Optional[str]   = None  
    user_category: Optional[str]   = None  
    merchant:      Optional[str]   = None  
    amount:        Optional[float] = None  
    category:      Optional[str]   = None  


#   Get all transactions  
@router.get("/")
def get_all_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).order_by(
        Transaction.transaction_date.desc()
    ).all()


#   Get transactions for a specific statement  
@router.get("/statement/{statement_id}")
def get_transactions_by_statement(statement_id: int, db: Session = Depends(get_db)):
    return db.query(Transaction).filter(
        Transaction.statement_id == statement_id
    ).order_by(Transaction.transaction_date.desc()).all()


#   Get transactions for a specific card  
@router.get("/card/{card_id}")
def get_transactions_by_card(card_id: int, db: Session = Depends(get_db)):
    return db.query(Transaction).filter(
        Transaction.card_id == card_id
    ).order_by(Transaction.transaction_date.desc()).all()


#   Category wise spending summary  
@router.get("/summary/categories")
def get_category_summary(db: Session = Depends(get_db)):
    results = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count")
    ).filter(
        Transaction.transaction_type == "debit"
    ).group_by(Transaction.category).all()

    return [
        {"category": r.category, "total": r.total, "count": r.count}
        for r in results
    ]


#   Merchant wise spending summary  
@router.get("/summary/merchants")
def get_merchant_summary(db: Session = Depends(get_db)):
    results = db.query(
        Transaction.merchant,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count")
    ).filter(
        Transaction.transaction_type == "debit"
    ).group_by(Transaction.merchant).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(20).all()

    return [
        {"merchant": r.merchant, "total": r.total, "count": r.count}
        for r in results
    ]


#   Get all EMI transactions  
@router.get("/emis")
def get_emi_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).filter(
        Transaction.is_emi == "yes"
    ).order_by(Transaction.transaction_date.desc()).all()


#   Get all subscription transactions  
@router.get("/subscriptions")
def get_subscription_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).filter(
        Transaction.is_subscription == "yes"
    ).order_by(Transaction.transaction_date.desc()).all()

  
# Updates the fields 
@router.patch("/{txn_id}")
def update_transaction(
    txn_id: int,
    update: TransactionUpdate,
    db: Session = Depends(get_db)
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Only update fields explicitly provided in the request
    if update.user_note is not None:
        txn.user_note = update.user_note
    if update.user_category is not None:
        txn.user_category = update.user_category
    if update.merchant is not None:
        txn.merchant = update.merchant
    if update.amount is not None:
        txn.amount = update.amount
    if update.category is not None:
        txn.category = update.category

    db.commit()
    db.refresh(txn)
    return {"message": "Transaction updated", "id": txn_id}


#   DELETE transaction  
@router.delete("/{txn_id}")
def delete_transaction(
    txn_id: int,
    db: Session = Depends(get_db)
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
    return {"message": "Transaction deleted", "id": txn_id}