import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy.orm import Session
from models.base import SessionLocal
from models.card import Card
from models.statement import Statement
from models.setting import Setting
from services.gmail_service import (
    get_gmail_service,
    search_statement_emails,
    get_email_details,
    download_pdf_attachment
)
from services.pdf_service import extract_text_from_pdf
from services.llm_service import extract_transactions_from_text
from models.transaction import Transaction
import subprocess
import tempfile


def get_setting(db: Session, key: str) -> str:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else None


def update_setting(db: Session, key: str, value: str):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    db.commit()


def is_scheduler_enabled(db: Session) -> bool:
    value = get_setting(db, 'scheduler_enabled')
    return value == 'true'


def run_dbt():
    try:
        dbt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..", "dbt_project"
        )
        result = subprocess.run(
            ["dbt", "run"],
            cwd=os.path.abspath(dbt_path),
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print("dbt run completed successfully")
        else:
            print(f"dbt run failed: {result.stderr}")
    except Exception as e:
        print(f"Error running dbt: {str(e)}")


def import_latest_statements():
    db = SessionLocal()

    try:
        if not is_scheduler_enabled(db):
            print("Scheduler is disabled — skipping import")
            return

        print(f"\n{'='*50}")
        print(f"Starting statement import — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        update_setting(db, 'scheduler_last_run', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        try:
            gmail_service = get_gmail_service()
        except Exception as e:
            print(f"Gmail authentication failed: {str(e)}")
            return

        cards = db.query(Card).filter(
            Card.is_active == 'yes',
            Card.email_sender != None,
            Card.email_sender != ''
        ).all()

        print(f"Processing {len(cards)} cards with email configured")

        imported_count = 0
        skipped_count = 0

        for card in cards:
            print(f"\nChecking {card.bank_name} {card.card_nickname}...")

            try:
                messages = search_statement_emails(
                    gmail_service,
                    card.email_sender,
                    days_back=45
                )

                if not messages:
                    print(f"  No statement email found — skipping")
                    skipped_count += 1
                    continue

                latest_message = messages[0]
                message_id = latest_message['id']

                existing = db.query(Statement).filter(
                    Statement.gmail_message_id == message_id
                ).first()

                if existing:
                    print(f"  Already imported (message ID: {message_id}) — skipping")
                    skipped_count += 1
                    continue

                email_details = get_email_details(gmail_service, message_id)
                if not email_details:
                    print(f"  Could not get email details — skipping")
                    skipped_count += 1
                    continue

                print(f"  Found new statement: {email_details['subject']}")

                pdf_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "uploads",
                    f"{card.bank_name}_{card.id}_{message_id[:8]}.pdf"
                )

                downloaded_path = download_pdf_attachment(
                    gmail_service,
                    message_id,
                    pdf_path
                )

                if not downloaded_path:
                    print(f"  No PDF attachment found — skipping")
                    skipped_count += 1
                    continue

                pdf_password = card.pdf_password or None
                raw_text = extract_text_from_pdf(downloaded_path, password=pdf_password)

                if not raw_text.strip():
                    print(f"  Could not extract text from PDF — skipping")
                    skipped_count += 1
                    continue

                print(f"  Parsing with Gemini AI...")
                extracted_data = extract_transactions_from_text(raw_text, card.bank_name)

                details = extracted_data.get("statement_details", {})

                def parse_date(date_str):
                    if not date_str:
                        return None
                    try:
                        return datetime.strptime(date_str, "%Y-%m-%d").date()
                    except:
                        return None

                from datetime import date
                total_amount = float(details.get("total_amount_due") or 0)

                if total_amount == 0:
                    print(f"  Zero bill statement — recording but marking as Paid")

                new_statement = Statement(
                    card_id=card.id,
                    statement_month=datetime.now().strftime("%B %Y"),
                    statement_date=parse_date(details.get("statement_date")),
                    statement_period_start=parse_date(details.get("statement_period_start")),
                    statement_period_end=parse_date(details.get("statement_period_end")),
                    due_date=parse_date(details.get("due_date")) or date.today(),
                    total_amount=total_amount,
                    minimum_due=float(details.get("minimum_amount_due") or 0),
                    opening_balance=float(details.get("opening_balance") or 0),
                    status="Paid" if total_amount == 0 else "Unpaid",
                    amount_paid=0,
                    outstanding=total_amount,
                    gmail_message_id=message_id    
                )

                db.add(new_statement)
                db.flush()

                transactions_saved = 0
                for txn in extracted_data.get("transactions", []):
                    txn_time = None
                    if txn.get("transaction_time"):
                        try:
                            parsed_time = datetime.strptime(
                                txn.get("transaction_time"), "%H:%M:%S"
                            )
                            txn_time = parsed_time.time()
                        except:
                            txn_time = None

                    new_transaction = Transaction(
                        statement_id=new_statement.id,
                        card_id=card.id,
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

                print(f"  ✅ Imported: ₹{total_amount:,.2f} due, {transactions_saved} transactions")
                imported_count += 1

                if os.path.exists(downloaded_path):
                    os.remove(downloaded_path)

            except Exception as e:
                print(f"  Error processing {card.bank_name}: {str(e)}")
                db.rollback()
                continue

        print(f"\n{'='*50}")
        print(f"Import complete — {imported_count} imported, {skipped_count} skipped")
        print(f"{'='*50}\n")

        if imported_count > 0:
            print("Running dbt to refresh analytics...")
            run_dbt()

        from datetime import timedelta
        next_run = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d 09:00:00')
        update_setting(db, 'scheduler_next_run', next_run)

    except Exception as e:
        print(f"Scheduler error: {str(e)}")

    finally:
        db.close()


def send_due_date_reminders():
    db = SessionLocal()

    try:
        if not is_scheduler_enabled(db):
            return

        from models.statement import Statement
        from datetime import date, timedelta

        today = date.today()

        upcoming = db.query(Statement).filter(
            Statement.status != 'Paid',
            Statement.due_date >= today,
            Statement.due_date <= today + timedelta(days=7)
        ).all()

        if not upcoming:
            print("No upcoming due dates")
            return

        print(f"Found {len(upcoming)} upcoming payments")

        for stmt in upcoming:
            days_left = (stmt.due_date - today).days
            card = db.query(Card).filter(Card.id == stmt.card_id).first()

            if days_left in [7, 3, 1, 0]:
                message = (
                    f"💳 CardSense Alert!\n"
                    f"Card: {card.bank_name} {card.card_nickname}\n"
                    f"Amount Due: ₹{stmt.outstanding:,.2f}\n"
                    f"Due Date: {stmt.due_date.strftime('%d %b %Y')}\n"
                    f"Days Left: {days_left}"
                )
                print(f"Sending reminder: {message}")

                from services.notification_service import send_whatsapp, send_email
                send_whatsapp(message)
                send_email(
                    subject=f"Payment Due in {days_left} days — {card.bank_name}",
                    body=message
                )

    except Exception as e:
        print(f"Reminder error: {str(e)}")
    finally:
        db.close()