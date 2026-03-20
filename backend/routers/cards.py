from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import get_db
from models.card import Card
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# Pydantic schema 
class CardCreate(BaseModel):
    bank_name: str
    card_nickname: str
    last_four_digits: str
    statement_day: Optional[int] = None
    due_day: Optional[int] = None
    credit_limit: Optional[int] = None
    email_sender: Optional[str] = None
    pdf_password: Optional[str] = None
    shared_group_id:   Optional[int]  = None

# GET all cards
@router.get("/")
def get_all_cards(db: Session = Depends(get_db)):
    cards = db.query(Card).filter(Card.is_active == "yes").all()
    return cards

# POST — add a new card
@router.post("/")
def add_card(card: CardCreate, db: Session = Depends(get_db)):
    new_card = Card(**card.dict())
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return {"message": "Card added successfully", "card": new_card}

# DELETE — deactivate a card
@router.delete("/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.is_active = "no"
    db.commit()
    return {"message": "Card deactivated"}


@router.patch("/{card_id}/password")
def update_card_password(card_id: int, password: str, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.pdf_password = password
    db.commit()
    return {"message": "Password updated successfully"}

    if update.shared_group_id is not None:
        card.shared_group_id = update.shared_group_id


# GET /cards/all
@router.get("/all")
def get_all_cards_including_inactive(db: Session = Depends(get_db)):
    from sqlalchemy import text
    results = db.execute(text("""
        select
            id, bank_name, card_nickname, last_four_digits,
            statement_day, due_day, credit_limit,
            email_sender, pdf_password, is_active
        from public.cards
        order by bank_name
    """)).fetchall()

    return [dict(row._mapping) for row in results]


@router.get("/utilization")
def get_cards_utilization(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            c.id,
            c.bank_name || ' ' || c.card_nickname as card_display_name,
            c.credit_limit,
            c.shared_group_id,
            coalesce(s.outstanding, 0) as used,
            case when c.credit_limit > 0
                 then round(coalesce(s.outstanding, 0)
                      / c.credit_limit * 100, 1)
                 else 0 end as utilization_pct
        from public.cards c
        left join public.statements s on s.id = (
            select id from public.statements
            where card_id = c.id and status != 'Paid'
            order by due_date desc limit 1
        )
        where c.is_active = 'yes'
        order by c.bank_name
    """)).fetchall()
    return [dict(row._mapping) for row in results]