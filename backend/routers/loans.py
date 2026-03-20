from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.base import get_db
from models.loan import Loan
from models.loan_payment import LoanPayment
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

router = APIRouter()


# Pydantic schemas
class LoanCreate(BaseModel):
    lender_name:           str
    loan_type:             str = 'Personal'
    loan_nickname:         Optional[str]  = None
    principal_amount:      float
    interest_rate:         float
    tenure_months:         int
    start_date:            str            
    emi_amount:            float
    emi_date:              int = 5
    outstanding_principal: float
    notes:                 Optional[str]  = None


class LoanUpdate(BaseModel):
    lender_name:           Optional[str]   = None
    loan_type:             Optional[str]   = None
    loan_nickname:         Optional[str]   = None
    interest_rate:         Optional[float] = None
    emi_amount:            Optional[float] = None
    emi_date:              Optional[int]   = None
    outstanding_principal: Optional[float] = None
    status:                Optional[str]   = None
    notes:                 Optional[str]   = None


class LoanPaymentCreate(BaseModel):
    loan_id:             int
    payment_date:        str    
    amount_paid:         float
    principal_component: Optional[float] = None
    interest_component:  Optional[float] = None
    reference_number:    Optional[str]   = None
    notes:               Optional[str]   = None


# GET all loans
@router.get("/")
def get_all_loans(db: Session = Depends(get_db)):
    loans = db.query(Loan).order_by(Loan.status, Loan.emi_date).all()
    return loans


# GET  active loans
@router.get("/active")
def get_active_loans(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            id,
            lender_name,
            loan_type,
            loan_nickname,
            emi_amount,
            emi_date,
            outstanding_principal,
            total_paid,
            principal_amount,
            interest_rate,
            tenure_months,
            start_date,
            status,
            case
                when extract(day from current_date)::int <= emi_date
                then date_trunc('month', current_date)::date
                     + (emi_date - 1)
                else (date_trunc('month', current_date)
                     + interval '1 month')::date
                     + (emi_date - 1)
            end as next_emi_date,
            case
                when extract(day from current_date)::int <= emi_date
                then emi_date - extract(day from current_date)::int
                else (
                    (date_trunc('month', current_date)
                     + interval '1 month')::date
                     + (emi_date - 1)
                     - current_date
                )::int
            end as days_until_emi,
            greatest(
                tenure_months - (
                    extract(year from age(current_date, start_date))::int * 12
                    + extract(month from age(current_date, start_date))::int
                ), 0
            ) as months_remaining,
            case
                when principal_amount > 0
                then round(total_paid / principal_amount * 100, 1)
                else 0
            end as pct_paid
        from public.loans
        where status = 'Active'
        order by emi_date asc
    """)).fetchall()

    return [dict(row._mapping) for row in results]


# GET   closed loans
@router.get("/closed")
def get_closed_loans(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            id,
            lender_name,
            loan_type,
            loan_nickname,
            emi_amount,
            emi_date,
            outstanding_principal,
            total_paid,
            principal_amount,
            interest_rate,
            tenure_months,
            start_date,
            status,
            0 as days_until_emi,
            0 as months_remaining,
            case
                when principal_amount > 0
                then round(total_paid / principal_amount * 100, 1)
                else 100
            end as pct_paid
        from public.loans
        where status = 'Closed'
        order by start_date desc
    """)).fetchall()

    return [dict(row._mapping) for row in results]

# log EMI payment
@router.post("/payments/")
def log_loan_payment(
    payment: LoanPaymentCreate,
    db: Session = Depends(get_db)
):
    loan = db.query(Loan).filter(Loan.id == payment.loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    try:
        pay_date = datetime.strptime(
            payment.payment_date, "%Y-%m-%d"
        ).date()
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # interest = outstanding * monthly_rate
    monthly_rate = float(loan.interest_rate) / 12 / 100
    interest_comp = payment.interest_component
    principal_comp = payment.principal_component

    if interest_comp is None:
        interest_comp = round(
            float(loan.outstanding_principal) * monthly_rate, 2
        )
    if principal_comp is None:
        principal_comp = round(
            float(payment.amount_paid) - interest_comp, 2
        )

    new_payment = LoanPayment(
        loan_id=payment.loan_id,
        payment_date=pay_date,
        amount_paid=payment.amount_paid,
        principal_component=principal_comp,
        interest_component=interest_comp,
        reference_number=payment.reference_number,
        notes=payment.notes
    )
    db.add(new_payment)

    # Update loan outstanding and total paid
    loan.outstanding_principal = max(
        float(loan.outstanding_principal) - principal_comp, 0
    )
    loan.total_paid = float(loan.total_paid) + float(payment.amount_paid)

    # Auto-close loan if fully paid
    if loan.outstanding_principal <= 0:
        loan.status = 'Closed'

    db.commit()
    db.refresh(new_payment)
    return {
        "message": "Payment logged",
        "id": new_payment.id,
        "principal_component": principal_comp,
        "interest_component": interest_comp
    }

@router.get("/all-payments")
def get_all_loan_payments(db: Session = Depends(get_db)):
    """Returns payments for all loans in one request"""
    results = db.execute(text("""
        select
            lp.id, lp.loan_id, lp.payment_date,
            lp.amount_paid, lp.principal_component,
            lp.interest_component,
            l.lender_name, l.loan_type, l.loan_nickname,
            to_char(lp.payment_date, 'YYYY-MM') as month_key,
            to_char(lp.payment_date, 'Mon YYYY') as month_label
        from public.loan_payments lp
        join public.loans l on l.id = lp.loan_id
        order by lp.payment_date desc
    """)).fetchall()
    return [dict(row._mapping) for row in results]

# GET   a single loan
@router.get("/{loan_id}")
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan

# GET loans detail
@router.get("/{loan_id}/detail")
def get_loan_detail(loan_id: int, db: Session = Depends(get_db)):
    result = db.execute(text("""
        select
            id, lender_name, loan_type, loan_nickname,
            principal_amount, interest_rate, tenure_months,
            start_date, emi_amount, emi_date,
            outstanding_principal, total_paid, status, notes
        from public.loans
        where id = :loan_id
    """), {"loan_id": loan_id}).fetchone()

    if not result:
        return None

    return dict(result._mapping)

# GET loan payment history
@router.get("/{loan_id}/payments")
def get_loan_payments(
    loan_id: int,
    db: Session = Depends(get_db)
):
    payments = db.query(LoanPayment).filter(
        LoanPayment.loan_id == loan_id
    ).order_by(LoanPayment.payment_date.desc()).all()
    return payments


# create loan
@router.post("/")
def create_loan(loan: LoanCreate, db: Session = Depends(get_db)):
    try:
        start = datetime.strptime(loan.start_date, "%Y-%m-%d").date()
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    new_loan = Loan(
        lender_name=loan.lender_name,
        loan_type=loan.loan_type,
        loan_nickname=loan.loan_nickname,
        principal_amount=loan.principal_amount,
        interest_rate=loan.interest_rate,
        tenure_months=loan.tenure_months,
        start_date=start,
        emi_amount=loan.emi_amount,
        emi_date=loan.emi_date,
        outstanding_principal=loan.outstanding_principal,
        total_paid=loan.principal_amount - loan.outstanding_principal,
        status='Active',
        notes=loan.notes
    )
    db.add(new_loan)
    db.commit()
    db.refresh(new_loan)
    return {"message": "Loan created", "id": new_loan.id}


# Pupdate loan
@router.patch("/{loan_id}")
def update_loan(
    loan_id: int,
    update: LoanUpdate,
    db: Session = Depends(get_db)
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if update.lender_name is not None:
        loan.lender_name = update.lender_name
    if update.loan_type is not None:
        loan.loan_type = update.loan_type
    if update.loan_nickname is not None:
        loan.loan_nickname = update.loan_nickname
    if update.interest_rate is not None:
        loan.interest_rate = update.interest_rate
    if update.emi_amount is not None:
        loan.emi_amount = update.emi_amount
    if update.emi_date is not None:
        loan.emi_date = update.emi_date
    if update.outstanding_principal is not None:
        loan.outstanding_principal = update.outstanding_principal
    if update.status is not None:
        loan.status = update.status
    if update.notes is not None:
        loan.notes = update.notes

    db.commit()
    return {"message": "Loan updated", "id": loan_id}


#DELETE loan
@router.delete("/{loan_id}")
def delete_loan(loan_id: int, db: Session = Depends(get_db)):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    db.delete(loan)
    db.commit()
    return {"message": "Loan deleted", "id": loan_id}


# DELETE loan payment
@router.delete("/payments/{payment_id}")
def delete_loan_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    payment = db.query(LoanPayment).filter(
        LoanPayment.id == payment_id
    ).first()
    if not payment:
        raise HTTPException(
            status_code=404, detail="Payment not found"
        )

    # Reverse outstanding update
    loan = db.query(Loan).filter(
        Loan.id == payment.loan_id
    ).first()
    if loan:
        loan.outstanding_principal = (
            float(loan.outstanding_principal)
            + float(payment.principal_component or 0)
        )
        loan.total_paid = max(
            float(loan.total_paid)
            - float(payment.amount_paid), 0
        )
        if loan.outstanding_principal > 0:
            loan.status = 'Active'

    db.delete(payment)
    db.commit()
    return {"message": "Payment deleted", "id": payment_id}


