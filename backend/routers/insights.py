from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.base import get_db
from services.llm_service import generate_insights
import json

router = APIRouter()


# GET insights generate
# Reads from analytics (dbt marts)
@router.get("/generate")
def generate_ai_insights(db: Session = Depends(get_db)):
    try:
        category_result = db.execute(text("""
            select
                category,
                sum(total_spend)       as total,
                sum(transaction_count) as count
            from analytics.spend_by_category
            group by category
            order by total desc
        """)).fetchall()

        category_summary = [
            {
                "category":     r[0],
                "total_spend":  float(r[1]),
                "transactions": int(r[2])
            }
            for r in category_result
        ]

        cards_result = db.execute(text("""
            select
                card_display_name, total_amount,
                outstanding, status, days_until_due
            from analytics.monthly_card_summary
            order by due_date asc
        """)).fetchall()

        cards_summary = [
            {
                "card":          r[0],
                "total_amount":  float(r[1]),
                "outstanding":   float(r[2]),
                "status":        r[3],
                "days_until_due": int(r[4]) if r[4] else None
            }
            for r in cards_result
        ]

        insights = generate_insights(
            transactions_summary=json.dumps(category_summary, indent=2),
            cards_summary=json.dumps(cards_summary, indent=2)
        )

        return {"insights": insights}

    except Exception as e:
        return {"insights": [f"Error generating insights: {str(e)}"]}


# GET insights spend-by-category 
@router.get("/spend-by-category")
def get_spend_by_category(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            card_id,
            card_display_name,
            bank_name,
            transaction_month,
            category,
            transaction_count,
            total_spend,
            avg_transaction,
            max_transaction,
            min_transaction
        from analytics.spend_by_category
        order by transaction_month asc, total_spend desc
    """)).fetchall()

    return [dict(row._mapping) for row in results]


# GET insights spend-trends 
@router.get("/spend-trends")
def get_spend_trends(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            card_id,
            card_display_name,
            bank_name,
            transaction_month,
            month_start,
            transaction_count,
            total_spend,
            avg_transaction,
            unique_merchants,
            emi_count,
            emi_spend,
            subscription_count,
            subscription_spend,
            rolling_3m_avg,
            is_anomaly
        from analytics.spend_trends
        order by month_start asc
    """)).fetchall()

    return [dict(row._mapping) for row in results]


# GET insights merchants 
@router.get("/merchants")
def get_merchant_analysis(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            merchant,
            category,
            card_id,
            card_display_name,
            bank_name,
            total_transactions,
            total_spend,
            avg_spend,
            last_transacted,
            first_transacted,
            has_emi,
            has_subscription,
            months_active
        from analytics.merchant_analysis
        order by total_spend desc
        limit 100
    """)).fetchall()

    return [dict(row._mapping) for row in results]


# GET insights reconciliation
@router.get("/reconciliation")
def get_payment_reconciliation(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            statement_id,
            card_id,
            card_display_name,
            bank_name,
            masked_card_number,
            statement_month,
            billing_period_display,
            due_date,
            status,
            is_overdue,
            days_until_due,
            opening_balance,
            charges_this_period,
            payments_received,
            closing_balance,
            minimum_due,
            payment_progress_pct,
            interest_risk,
            estimated_interest,
            payment_breakdown
        from analytics.payment_reconciliation
        order by due_date desc
    """)).fetchall()

    return [dict(row._mapping) for row in results]