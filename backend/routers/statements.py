from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from models import get_db
from models.statement import Statement
from models.transaction import Transaction
from models.card import Card
from services.pdf_service import extract_text_from_pdf, save_uploaded_pdf
from services.llm_service import extract_transactions_from_text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter()

# Pydantic schema
class StatementUpdate(BaseModel):
    due_date:        Optional[str]   = None
    total_amount:    Optional[float] = None
    minimum_due:     Optional[float] = None
    status:          Optional[str]   = None
    statement_month: Optional[str]   = None


# Get all statements
@router.get("/")
def get_all_statements(db: Session = Depends(get_db)):
    statements = db.query(Statement).order_by(
        Statement.due_date.desc()
    ).all()
    return statements


# Get statements for a specific card
@router.get("/card/{card_id}")
def get_statements_by_card(card_id: int, db: Session = Depends(get_db)):
    return db.query(Statement).filter(
        Statement.card_id == card_id
    ).order_by(Statement.due_date.desc()).all()


#   Get a single statement with all its transactions  
@router.get("/{statement_id}")
def get_statement_detail(statement_id: int, db: Session = Depends(get_db)):
    statement = db.query(Statement).filter(
        Statement.id == statement_id
    ).first()

    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    # Get all transactions for this statement
    transactions = db.query(Transaction).filter(
        Transaction.statement_id == statement_id
    ).order_by(Transaction.transaction_date.desc()).all()

    return {
        "statement": statement,
        "transactions": transactions,
        "transaction_count": len(transactions)
    }


#   Upload PDF and auto-parse with Gemini  
@router.post("/upload-pdf")
async def upload_and_parse_statement(
    card_id: int = Form(...),
    bank_name: str = Form(...),
    pdf_password: Optional[str] = Form(None),
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # Verify card exists
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Save the uploaded PDF
    file_bytes = await pdf_file.read()
    file_path = save_uploaded_pdf(file_bytes, pdf_file.filename)

    try:
        # Extract text from PDF
        print(f"Extracting text from {pdf_file.filename}...")
        raw_text = extract_text_from_pdf(file_path, password=pdf_password)

        if not raw_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from PDF. Check if password is correct."
            )

        print(f"Extracted {len(raw_text)} characters from PDF")

        # Send to Gemini
        print("Sending to Gemini for transaction extraction...")
        extracted_data = extract_transactions_from_text(raw_text, bank_name)

        # Save statement to db
        details = extracted_data.get("statement_details", {})

        # Parse dates
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                return None

        new_statement = Statement(
            card_id=card_id,
            statement_month=datetime.now().strftime("%B %Y"),
            statement_date=parse_date(details.get("statement_date")),
            statement_period_start=parse_date(details.get("statement_period_start")),  
            statement_period_end=parse_date(details.get("statement_period_end")),      
            due_date=parse_date(details.get("due_date")) or date.today(),
            total_amount=float(details.get("total_amount_due") or 0),
            minimum_due=float(details.get("minimum_amount_due") or 0),
            opening_balance=float(details.get("opening_balance") or 0),
            status="Unpaid",
            pdf_text=raw_text,
            amount_paid=0,
            outstanding=float(details.get("total_amount_due") or 0)
        )

        db.add(new_statement)
        db.flush()  

        # Savetransactions to db
        transactions_saved = 0
        for txn in extracted_data.get("transactions", []):

            # Parse time
            txn_time = None
            if txn.get("transaction_time"):
                try:
                    from datetime import time as dt_time
                    time_str = txn.get("transaction_time")
                    parsed_time = datetime.strptime(time_str, "%H:%M:%S")
                    txn_time = parsed_time.time()
                except:
                    txn_time = None

            new_transaction = Transaction(
                statement_id=new_statement.id,
                card_id=card_id,
                transaction_date=parse_date(txn.get("transaction_date")) or date.today(),
                transaction_time=txn_time,                           
                merchant=txn.get("merchant", "Unknown"),
                description=txn.get("description", ""),
                amount=float(txn.get("amount") or 0),
                transaction_type=txn.get("transaction_type", "debit"),
                category=txn.get("category", "Other"),
                is_emi=txn.get("is_emi", "no"),
                is_subscription=txn.get("is_subscription", "no")
            )
            db.add(new_transaction)
            transactions_saved += 1

        db.commit()
        db.refresh(new_statement)

        return {
            "message": "Statement parsed and saved successfully!",
            "statement_id": new_statement.id,
            "total_amount": new_statement.total_amount,
            "due_date": new_statement.due_date,
            "transactions_extracted": transactions_saved,
            "summary": extracted_data.get("summary", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )
    finally:
        # delete the uploaded file after process
        if os.path.exists(file_path):
            os.remove(file_path)


#   Manually add a statement 
class StatementCreate(BaseModel):
    card_id: int
    statement_month: str
    statement_date: Optional[date] = None
    due_date: date
    total_amount: float
    minimum_due: Optional[float] = None
    opening_balance: Optional[float] = 0
    pdf_link: Optional[str] = None

@router.post("/manual")
def add_statement_manually(statement: StatementCreate, db: Session = Depends(get_db)):
    new_statement = Statement(
        **statement.dict(),
        status="Unpaid",
        amount_paid=0,
        outstanding=statement.total_amount
    )
    db.add(new_statement)
    db.commit()
    db.refresh(new_statement)
    return {"message": "Statement added successfully", "statement": new_statement}


#   Update PDF link for a statement  
@router.patch("/{statement_id}/pdf-link")
def update_pdf_link(
    statement_id: int,
    pdf_link: str,
    db: Session = Depends(get_db)
):
    statement = db.query(Statement).filter(Statement.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    statement.pdf_link = pdf_link
    db.commit()
    return {"message": "PDF link updated successfully"}

 
# editing due date, amounts, and status from the UI
@router.patch("/{statement_id}")
def update_statement(
    statement_id: int,
    update: StatementUpdate,
    db: Session = Depends(get_db)
):
    from datetime import datetime
    stmt = db.query(Statement).filter(
        Statement.id == statement_id
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    if update.due_date:
        stmt.due_date = datetime.strptime(update.due_date, "%Y-%m-%d").date()
    if update.total_amount is not None:
        stmt.total_amount = update.total_amount
        # Recalculate outstanding when total changes
        stmt.outstanding = update.total_amount - (stmt.amount_paid or 0)
    if update.minimum_due is not None:
        stmt.minimum_due = update.minimum_due
    if update.status:
        stmt.status = update.status
    if update.statement_month:
        stmt.statement_month = update.statement_month

    db.commit()
    return {"message": "Statement updated", "id": statement_id}


# Deletes statement
@router.delete("/{statement_id}")
def delete_statement(
    statement_id: int,
    db: Session = Depends(get_db)
):
    stmt = db.query(Statement).filter(
        Statement.id == statement_id
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    db.delete(stmt)
    db.commit()
    return {"message": "Statement deleted", "id": statement_id}
