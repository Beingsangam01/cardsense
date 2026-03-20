from fastapi import APIRouter, Depends
import requests as http_requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.base import get_db
import subprocess
import os

router = APIRouter()


# GET dashboard summary
@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    result = db.execute(text("""
        select
            coalesce(sum(outstanding), 0)           as total_outstanding,
            coalesce(sum(total_amount), 0)          as total_billed,
            coalesce(sum(total_paid), 0)            as total_paid,
            count(*) filter (where is_overdue)      as overdue_count,
            count(*) filter (where is_due_soon)     as due_soon_count,
            count(*) filter (where status = 'Paid') as paid_count,
            count(*)                                as total_statements
        from analytics.monthly_card_summary
        where due_date >= date_trunc('month', current_date)
        and due_date < date_trunc('month', current_date)
              + interval '2 months'
    """)).fetchone()

    return {
        "total_outstanding": float(result.total_outstanding or 0),
        "total_billed":      float(result.total_billed or 0),
        "total_paid":        float(result.total_paid or 0),
        "overdue_count":     int(result.overdue_count or 0),
        "due_soon_count":    int(result.due_soon_count or 0),
        "paid_count":        int(result.paid_count or 0),
        "total_statements":  int(result.total_statements or 0)
    }


# GET dashboard cards
@router.get("/cards")
def get_all_cards_summary(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            card_display_name,
            bank_name,
            masked_card_number,
            credit_limit,
            statement_month,
            billing_period_display,
            due_date,
            days_until_due,
            total_amount,
            total_paid,
            outstanding,
            minimum_due,
            payment_progress_pct,
            status,
            is_overdue,
            is_due_soon,
            utilization_pct,
            pdf_link,
            statement_id,
            card_id
        from analytics.monthly_card_summary
        order by due_date asc
    """)).fetchall()

    return [dict(row._mapping) for row in results]


# GET dashboard alerts
@router.get("/alerts")
def get_due_soon_alerts(db: Session = Depends(get_db)):
    results = db.execute(text("""
        select
            c.id,
            c.bank_name,
            c.card_nickname,
            c.bank_name || ' ' || c.card_nickname as card_display_name,
            '•••• ' || c.last_four_digits          as masked_card_number,
            s.due_date,
            s.outstanding,
            s.minimum_due,
            s.status,
            (s.due_date - current_date) as days_until_due
        from public.statements s
        join public.cards c on c.id = s.card_id
        where
            s.status != 'Paid'
            and s.due_date is not null
            and s.due_date <= current_date + interval '7 days'
            and c.is_active = 'yes'
        order by s.due_date asc
    """)).fetchall()

    return [dict(row._mapping) for row in results]

# Triggers a dbt Cloud job run via the dbt Cloud API.
@router.post("/refresh")
def refresh_analytics():

    dbt_token      = os.getenv("DBT_CLOUD_TOKEN")
    dbt_account_id = os.getenv("DBT_CLOUD_ACCOUNT_ID")
    dbt_job_id     = os.getenv("DBT_CLOUD_JOB_ID")

    if not all([dbt_token, dbt_account_id, dbt_job_id]):
        return {
            "success": False,
            "message": "dbt Cloud not configured — run dbt manually"
        }

    # Trigger dbt Cloud job via API
    response = http_requests.post(
        f"https://cloud.getdbt.com/api/v2/accounts/"
        f"{dbt_account_id}/jobs/{dbt_job_id}/run/",
        headers={
            "Authorization": f"Token {dbt_token}",
            "Content-Type":  "application/json"
        },
        json={
            "cause": "Triggered from CardSense dashboard"
        },
        timeout=15
    )

    if response.status_code == 200:
        run_data = response.json().get("data", {})
        return {
            "success":    True,
            "message":    "dbt Cloud job triggered successfully. "
                          "Analytics will update in ~2 minutes.",
            "run_id":     run_data.get("id"),
            "monitor":    f"https://cloud.getdbt.com/deploy/"
                          f"{dbt_account_id}/runs/{run_data.get('id')}"
        }
    else:
        return {
            "success": False,
            "message": "Failed to trigger dbt Cloud job",
            "detail":  response.text
        }