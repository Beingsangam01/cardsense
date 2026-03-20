from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.base import get_db
from models.payment import Payment
from models.statement import Statement
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

router = APIRouter()


# Pydantic schemas
class PaymentCreate(BaseModel):
    card_id:          int
    statement_id:     Optional[int]  = None
    payment_date:     str                    
    amount:           float
    payment_type:     str                    
    reference_number: Optional[str]  = None
    notes:            Optional[str]  = None


class PaymentUpdate(BaseModel):
    payment_date:     Optional[str]   = None
    amount:           Optional[float] = None
    payment_type:     Optional[str]   = None
    reference_number: Optional[str]   = None
    notes:            Optional[str]   = None


# GET all payments
@router.get("/")
def get_payments(db: Session = Depends(get_db)):
    payments = db.query(Payment).order_by(
        Payment.payment_date.desc()
    ).all()
    return payments


# GET payments by card 
@router.get("/card/{card_id}")
def get_payments_by_card(
    card_id: int,
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).filter(
        Payment.card_id == card_id
    ).order_by(Payment.payment_date.desc()).all()
    return payments


# create payment
@router.post("/")
def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db)
):
    try:
        payment_date = datetime.strptime(
            payment.payment_date, "%Y-%m-%d"
        ).date()
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Create payment record
    new_payment = Payment(
        card_id=payment.card_id,
        statement_id=payment.statement_id,
        payment_date=payment_date,
        amount=payment.amount,
        payment_type=payment.payment_type,
        reference_number=payment.reference_number,
        notes=payment.notes
    )
    db.add(new_payment)

    if payment.statement_id:
        stmt = db.query(Statement).filter(
            Statement.id == payment.statement_id
        ).first()

        if stmt:
            stmt.amount_paid  = (stmt.amount_paid or 0) + payment.amount
            stmt.outstanding  = max(
                (stmt.total_amount or 0) - stmt.amount_paid, 0
            )

            if stmt.outstanding <= 0:
                stmt.status = "Paid"
            elif stmt.amount_paid > 0:
                stmt.status = "Partial"

    db.commit()
    db.refresh(new_payment)
    return {
        "message": "Payment logged successfully",
        "id": new_payment.id
    }


# update payment 
@router.patch("/{payment_id}")
def update_payment(
    payment_id: int,
    update: PaymentUpdate,
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()
    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    old_amount = payment.amount or 0

    if update.payment_date:
        payment.payment_date = datetime.strptime(
            update.payment_date, "%Y-%m-%d"
        ).date()
    if update.amount is not None:
        payment.amount = update.amount
    if update.payment_type:
        payment.payment_type = update.payment_type
    if update.reference_number is not None:
        payment.reference_number = update.reference_number
    if update.notes is not None:
        payment.notes = update.notes

    # Recalculate statement if amount changed
    if update.amount is not None and payment.statement_id:
        stmt = db.query(Statement).filter(
            Statement.id == payment.statement_id
        ).first()
        if stmt:
            stmt.amount_paid  = max(
                (stmt.amount_paid or 0) - old_amount + update.amount, 0
            )
            stmt.outstanding  = max(
                (stmt.total_amount or 0) - stmt.amount_paid, 0
            )
            if stmt.outstanding <= 0:
                stmt.status = "Paid"
            elif stmt.amount_paid > 0:
                stmt.status = "Partial"
            else:
                stmt.status = "Unpaid"

    db.commit()
    return {"message": "Payment updated", "id": payment_id}


#DELETE payment
@router.delete("/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()
    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    if payment.statement_id:
        stmt = db.query(Statement).filter(
            Statement.id == payment.statement_id
        ).first()
        if stmt:
            stmt.amount_paid  = max(
                (stmt.amount_paid or 0) - (payment.amount or 0), 0
            )
            stmt.outstanding  = max(
                (stmt.total_amount or 0) - stmt.amount_paid, 0
            )
            if stmt.outstanding <= 0:
                stmt.status = "Paid"
            elif stmt.amount_paid > 0:
                stmt.status = "Partial"
            else:
                stmt.status = "Unpaid"

    db.delete(payment)
    db.commit()
    return {"message": "Payment deleted", "id": payment_id}

# GET unpaid-statements
@router.get("/unpaid-statements")
def get_unpaid_statements(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            s.id                                          as statement_id,
            c.bank_name || ' ' || c.card_nickname
                || ' — ₹' || round(s.outstanding::numeric, 2)
                || ' due'                                 as display_name,
            s.outstanding,
            s.card_id,
            c.bank_name,
            c.card_nickname
        from public.statements s
        join public.cards c on s.card_id = c.id
        where s.status != 'Paid'
        order by s.due_date asc
    """)).fetchall()

    return [dict(row._mapping) for row in results]


# GET payments history
@router.get("/history")
def get_payment_history(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            p.payment_date,
            c.bank_name || ' ' || c.card_nickname as card,
            p.payment_amount,
            p.payment_type,
            p.reference_number,
            p.notes,
            p.payment_month
        from analytics.stg_payments p
        join public.cards c on p.card_id = c.id
        order by p.payment_date desc
    """)).fetchall()

    return [dict(row._mapping) for row in results]


# GET payments reconciliation
@router.get("/reconciliation/{statement_id}")
def get_statement_reconciliation(
    statement_id: int,
    db: Session = Depends(get_db)
):
    result = db.execute(text("""
        select
            opening_balance,
            charges_this_period,
            payments_received,
            closing_balance,
            minimum_due,
            payment_progress_pct,
            interest_risk,
            estimated_interest
        from analytics.payment_reconciliation
        where statement_id = :statement_id
    """), {"statement_id": statement_id}).fetchone()

    if not result:
        return None

    return dict(result._mapping)