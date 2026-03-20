import requests
import pandas as pd
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")
load_dotenv(ENV_PATH)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def _get(endpoint: str) -> requests.Response:
    return requests.get(BACKEND_URL + endpoint, timeout=15)


def _post(endpoint: str, **kwargs) -> requests.Response:
    return requests.post(BACKEND_URL + endpoint, timeout=30, **kwargs)


def _patch(endpoint: str, **kwargs) -> requests.Response:
    return requests.patch(BACKEND_URL + endpoint, timeout=15, **kwargs)


def _delete(endpoint: str) -> requests.Response:
    return requests.delete(BACKEND_URL + endpoint, timeout=15)


 
# DASHBOARD


def get_dashboard_summary() -> dict:
    try:
        r = _get("/dashboard/summary")
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def get_all_cards_summary() -> pd.DataFrame:
    try:
        r = _get("/dashboard/cards")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_due_soon_alerts() -> pd.DataFrame:
    try:
        r = _get("/dashboard/alerts")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def refresh_analytics() -> dict:
    try:
        r = _post("/dashboard/refresh")
        return r.json() if r.status_code == 200 else {"success": False}
    except Exception as e:
        return {"success": False, "message": str(e)}


   
# CARDS
  

def get_active_cards() -> pd.DataFrame:
    try:
        r = _get("/cards/")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_all_cards() -> pd.DataFrame:
    try:
        r = _get("/cards/all")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def add_card(payload: dict) -> dict:
    try:
        r = _post("/cards/", json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def update_card_password(card_id: int, password: str) -> dict:
    try:
        r = _patch(f"/cards/{card_id}/password",
                   params={"password": password})
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def deactivate_card(card_id: int) -> dict:
    try:
        r = _delete(f"/cards/{card_id}")
        return r.json()
    except Exception as e:
        return {"error": str(e)}


 
# STATEMENTS
   

def get_statements_for_card(card_id: int) -> pd.DataFrame:
    try:
        r = _get(f"/statements/card/{card_id}")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_statement_detail(statement_id: int) -> dict:
    try:
        r = _get(f"/statements/{statement_id}")
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def upload_statement_pdf(card_id: int, bank_name: str,
                         pdf_password: str, file_bytes: bytes,
                         filename: str) -> dict:
    try:
        files = {"pdf_file": (filename, file_bytes, "application/pdf")}
        data  = {
            "card_id":      card_id,
            "bank_name":    bank_name,
            "pdf_password": pdf_password or ""
        }
        r = _post("/statements/upload-pdf", files=files, data=data)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def update_pdf_link(statement_id: int, pdf_link: str) -> dict:
    try:
        r = _patch(f"/statements/{statement_id}/pdf-link",
                   params={"pdf_link": pdf_link})
        return r.json()
    except Exception as e:
        return {"error": str(e)}



# TRANSACTIONS
   

def get_transactions_for_statement(statement_id: int) -> pd.DataFrame:
    try:
        r = _get(f"/transactions/statement/{statement_id}")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def update_transaction(txn_id: int, payload: dict) -> dict:
    try:
        r = _patch(f"/transactions/{txn_id}", json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def delete_transaction(txn_id: int) -> dict:
    try:
        r = _delete(f"/transactions/{txn_id}")
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# PAYMENTS

def get_unpaid_statements() -> pd.DataFrame:
    try:
        r = _get("/payments/unpaid-statements")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_payment_history() -> pd.DataFrame:
    try:
        r = _get("/payments/history")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_statement_reconciliation(statement_id: int) -> dict:
    try:
        r = _get(f"/payments/reconciliation/{statement_id}")
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

def get_all_loan_payments() -> pd.DataFrame:
    try:
        r = _get("/loans/all-payments")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def log_payment(payload: dict) -> dict:
    try:
        r = _post("/payments/", json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def delete_payment(payment_id: int) -> dict:
    try:
        r = _delete(f"/payments/{payment_id}")
        return r.json()
    except Exception as e:
        return {"error": str(e)}



# LOANS

def get_active_loans() -> pd.DataFrame:
    try:
        r = _get("/loans/active")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_closed_loans() -> pd.DataFrame:
    try:
        r = _get("/loans/closed")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_loan_detail(loan_id: int) -> dict:
    try:
        r = _get(f"/loans/{loan_id}/detail")
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def get_loan_payments(loan_id: int) -> list:
    try:
        r = _get(f"/loans/{loan_id}/payments")
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def add_loan(payload: dict) -> dict:
    try:
        r = _post("/loans/", json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def update_loan(loan_id: int, payload: dict) -> dict:
    try:
        r = _patch(f"/loans/{loan_id}", json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def delete_loan(loan_id: int) -> dict:
    try:
        r = _delete(f"/loans/{loan_id}")
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def log_loan_payment(payload: dict) -> dict:
    try:
        r = _post("/loans/payments/", json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def delete_loan_payment(payment_id: int) -> dict:
    try:
        r = _delete(f"/loans/payments/{payment_id}")
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# INSIGHTS


def get_spend_by_category() -> pd.DataFrame:
    try:
        r = _get("/insights/spend-by-category")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_spend_trends() -> pd.DataFrame:
    try:
        r = _get("/insights/spend-trends")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_merchant_analysis() -> pd.DataFrame:
    try:
        r = _get("/insights/merchants")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_payment_reconciliation() -> pd.DataFrame:
    try:
        r = _get("/insights/reconciliation")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_ai_insights() -> list:
    try:
        r = _get("/insights/generate")
        return r.json().get("insights", []) if r.status_code == 200 else []
    except Exception:
        return []

def get_cards_utilization() -> pd.DataFrame:
    try:
        r = _get("/cards/utilization")
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

   
# SHARED GROUPS
def get_shared_groups() -> list:
    try:
        r = _get("/shared-groups/")
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


# SCHEDULER

def get_scheduler_status() -> dict:
    try:
        r = _get("/scheduler/status")
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def enable_scheduler() -> dict:
    try:
        r = _post("/scheduler/enable")
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def disable_scheduler() -> dict:
    try:
        r = _post("/scheduler/disable")
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def run_import_now() -> dict:
    try:
        r = _post("/scheduler/run-now")
        return r.json()
    except Exception as e:
        return {"error": str(e)}