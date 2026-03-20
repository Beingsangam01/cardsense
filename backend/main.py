import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import cards, statements, payments, transactions, insights
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from scheduler.jobs import import_latest_statements, send_due_date_reminders
import atexit
from routers import shared_groups, loans, dashboard


app = FastAPI(
    title="CardSense API",
    description="Credit Card Statement Tracker with LLM-powered insights",
    version="1.0.0"
)

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(cards.router, prefix="/cards", tags=["Cards"])
app.include_router(statements.router, prefix="/statements", tags=["Statements"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(insights.router, prefix="/insights", tags=["Insights"])

app.include_router(shared_groups.router, prefix="/shared-groups", tags=["Shared Groups"])
app.include_router(loans.router, prefix="/loans", tags=["Loans"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# ── Scheduler Setup ──
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"

if SCHEDULER_ENABLED:
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        import_latest_statements,
        trigger=CronTrigger(hour=9, minute=0),
        id='import_statements',
        name='Import Latest Statements',
        replace_existing=True
    )

    scheduler.add_job(
        send_due_date_reminders,
        trigger=CronTrigger(hour=8, minute=0),
        id='send_reminders',
        name='Send Due Date Reminders',
        replace_existing=True
    )

    scheduler.start()
    print("✅ Scheduler started — imports at 9 AM, reminders at 8 AM daily")
    atexit.register(lambda: scheduler.shutdown())

else:
    print("⏸️ Scheduler disabled — set SCHEDULER_ENABLED=true to enable")


@app.get("/")
def root():
    return {"message": "CardSense API is running 🚀"}

@app.get("/kaithheathcheck")
def health_check():
    return {"status": "ok"}

@app.get("/kaithhealthcheck")
def health_check_alt():
    return {"status": "ok"}


# Scheduler Control Endpoints
@app.post("/scheduler/enable")
def enable_scheduler():
    from models.base import SessionLocal
    from scheduler.jobs import update_setting
    db = SessionLocal()
    update_setting(db, 'scheduler_enabled', 'true')
    db.close()
    return {"message": "Scheduler enabled ✅"}


@app.post("/scheduler/disable")
def disable_scheduler():
    from models.base import SessionLocal
    from scheduler.jobs import update_setting
    db = SessionLocal()
    update_setting(db, 'scheduler_enabled', 'false')
    db.close()
    return {"message": "Scheduler disabled ⏸️"}


@app.get("/scheduler/status")
def get_scheduler_status():
    from models.base import SessionLocal
    from scheduler.jobs import get_setting
    db = SessionLocal()
    enabled = get_setting(db, 'scheduler_enabled')
    last_run = get_setting(db, 'scheduler_last_run')
    next_run = get_setting(db, 'scheduler_next_run')
    db.close()
    return {
        "enabled": enabled == 'true',
        "last_run": last_run,
        "next_run": next_run
    }


@app.post("/scheduler/run-now")
def run_import_now():
    import threading
    thread = threading.Thread(target=import_latest_statements)
    thread.start()
    return {"message": "Import started in background — check logs for progress"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

