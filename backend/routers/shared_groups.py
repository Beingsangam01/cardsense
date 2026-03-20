from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.base import get_db
from models.shared_limit_group import SharedLimitGroup
from models.card import Card
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


#  Pydantic schemas
class GroupCreate(BaseModel):
    group_name:  str
    total_limit: int
    notes:       Optional[str] = None


class GroupUpdate(BaseModel):
    group_name:  Optional[str] = None
    total_limit: Optional[int] = None
    notes:       Optional[str] = None


# ET all groups
@router.get("/")
def get_all_groups(db: Session = Depends(get_db)):
    groups = db.query(SharedLimitGroup).all()

    result = []
    for g in groups:
        # Get cards in this group
        cards = db.query(Card).filter(
            Card.shared_group_id == g.id
        ).all()

        # Calculate total outstanding across group cards
        from models.statement import Statement
        total_used = 0
        for card in cards:
            latest = db.query(Statement).filter(
                Statement.card_id == card.id,
                Statement.status != 'Paid'
            ).order_by(Statement.due_date.desc()).first()
            if latest:
                total_used += float(latest.outstanding or 0)

        result.append({
            "id":           g.id,
            "group_name":   g.group_name,
            "total_limit":  g.total_limit,
            "notes":        g.notes,
            "cards":        [
                {
                    "id":           c.id,
                    "bank_name":    c.bank_name,
                    "card_nickname": c.card_nickname,
                    "last_four_digits": c.last_four_digits
                }
                for c in cards
            ],
            "total_used":      total_used,
            "available":       max(g.total_limit - total_used, 0),
            "utilization_pct": round(
                total_used / g.total_limit * 100
                if g.total_limit > 0 else 0, 1
            )
        })

    return result


# GET single group
@router.get("/{group_id}")
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(SharedLimitGroup).filter(
        SharedLimitGroup.id == group_id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


# create group
@router.post("/")
def create_group(
    group: GroupCreate,
    db: Session = Depends(get_db)
):
    new_group = SharedLimitGroup(
        group_name=group.group_name,
        total_limit=group.total_limit,
        notes=group.notes
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return {
        "message": "Group created",
        "id": new_group.id
    }


#  update group
@router.patch("/{group_id}")
def update_group(
    group_id: int,
    update: GroupUpdate,
    db: Session = Depends(get_db)
):
    group = db.query(SharedLimitGroup).filter(
        SharedLimitGroup.id == group_id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if update.group_name is not None:
        group.group_name = update.group_name
    if update.total_limit is not None:
        group.total_limit = update.total_limit
    if update.notes is not None:
        group.notes = update.notes

    db.commit()
    return {"message": "Group updated", "id": group_id}


# DELETE group
@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    group = db.query(SharedLimitGroup).filter(
        SharedLimitGroup.id == group_id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Unlink all cards from this group before deleting
    db.query(Card).filter(
        Card.shared_group_id == group_id
    ).update({"shared_group_id": None})

    db.delete(group)
    db.commit()
    return {"message": "Group deleted", "id": group_id}


# assign card to grou
@router.patch("/{group_id}/assign-card/{card_id}")
def assign_card_to_group(
    group_id: int,
    card_id: int,
    db: Session = Depends(get_db)
):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    group = db.query(SharedLimitGroup).filter(
        SharedLimitGroup.id == group_id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    card.shared_group_id = group_id
    db.commit()
    return {
        "message": "Card assigned to group",
        "card_id": card_id,
        "group_id": group_id
    }


#remove card from group
@router.patch("/remove-card/{card_id}")
def remove_card_from_group(
    card_id: int,
    db: Session = Depends(get_db)
):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    card.shared_group_id = None
    db.commit()
    return {
        "message": "Card removed from group",
        "card_id": card_id
    }