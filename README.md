# CardSense - Personal Finance Analytics Platform

> An automated personal finance platform that extracts credit card statements from Gmail, parses transactions via Gemini AI, and surfaces insights through a Streamlit dashboard built on dbt mart tables and a FastAPI REST API.

[![Live App](https://img.shields.io/badge/Live%20App-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://cardsense.streamlit.app)
[![API Docs](https://img.shields.io/badge/API%20Docs-Leapcell-6C63FF?style=for-the-badge&logo=fastapi&logoColor=white)](https://cardsense-sangamvaishkiyar7242-6rbqlyma.leapcell.dev/docs)

---

## What It Does

CardSense replaces manual credit card tracking with an automated pipeline:

- **Automatic ingestion** - connects to Gmail via Gmail API, detects new statement emails, downloads PDF attachments
- **AI extraction** - sends PDFs to Gemini AI which extracts every transaction, categorises it, and identifies EMIs and subscriptions
- **Data transformation** - dbt models transform raw transactions into analytics-ready mart tables scheduled via dbt Cloud
- **Analytics dashboard** - 6-page Streamlit app with spend anomaly detection, interest risk alerts, shared credit pool utilisation, and a loan prepayment calculator

---

## Architecture
```mermaid
flowchart TD
    A[Gmail API] -->|PDF statements| C
    B[Manual Upload] -->|PDF via browser| C
    C[Gemini AI API\nTransaction parsing] --> D

    D[FastAPI Backend\n55 endpoints]

    D -->|writes| E[(PostgreSQL\nSupabase\n9 raw tables)]
    E -->|transforms| F[dbt Cloud\n5 mart models]
    F -->|writes| G[(analytics schema\ndbt mart tables)]
    G -->|reads| D

    D -->|serves| H[Streamlit Dashboard\n6 pages]

    style A fill:#E6F1FB,stroke:#378ADD,color:#0C447C
    style B fill:#E6F1FB,stroke:#378ADD,color:#0C447C
    style C fill:#FAEEDA,stroke:#BA7517,color:#633806
    style D fill:#EEEDFE,stroke:#534AB7,color:#3C3489
    style E fill:#E1F5EE,stroke:#0F6E56,color:#085041
    style F fill:#FAECE7,stroke:#993C1D,color:#712B13
    style G fill:#E1F5EE,stroke:#0F6E56,color:#085041
    style H fill:#EEEDFE,stroke:#534AB7,color:#3C3489
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit, Plotly |
| Backend API | FastAPI, Uvicorn |
| AI / Extraction | Gemini AI API, Gmail API |
| Database | PostgreSQL on Supabase |
| Transformation | dbt Core (local) + dbt Cloud (production) |
| Deployment | Leapcell (backend), Streamlit Cloud (frontend) |

---

## Project Structure
```mermaid
graph TD
    Root[cardsense/]

    Root --> BE[backend/]
    Root --> FE[frontend/]
    Root --> DBT[dbt_project/]

    BE --> R[routers/\n55 endpoints]
    BE --> M[models/\n8 ORM models]
    BE --> S[services/\nGemini · PDF · Gmail]

    FE --> SC[services_client.py\nsingle API client]
    FE --> PG[pages/\n6 Streamlit pages]

    DBT --> MO[models/]
    MO --> ST[staging/\n4 models]
    MO --> MA[marts/\n5 models]

    style Root fill:#EEEDFE,stroke:#534AB7,color:#3C3489
    style BE fill:#E6F1FB,stroke:#378ADD,color:#0C447C
    style FE fill:#E6F1FB,stroke:#378ADD,color:#0C447C
    style DBT fill:#E6F1FB,stroke:#378ADD,color:#0C447C
    style SC fill:#FAEEDA,stroke:#BA7517,color:#633806
    style MA fill:#E1F5EE,stroke:#0F6E56,color:#085041
    style ST fill:#E1F5EE,stroke:#0F6E56,color:#085041
```

---

## Database Schema

**Raw tables** (`public.*`) - written by FastAPI:

| Table | Description |
|---|---|
| `cards` | Credit card details, limits, shared pool assignments |
| `statements` | Monthly statements with due dates and payment status |
| `transactions` | Individual transactions with AI-assigned categories |
| `payments` | Payment records with statement reconciliation |
| `loans` | Loan details with EMI schedule |
| `loan_payments` | Individual EMI payment records |
| `shared_limit_groups` | Shared credit pool groups across multiple cards |

**Mart tables** (`analytics.*`) - written by dbt, read by FastAPI:

| Model | Description |
|---|---|
| `spend_trends` | Monthly spend per card with rolling 3M average and anomaly flag |
| `spend_by_category` | Category breakdown per card per month |
| `merchant_analysis` | Top merchants with recurring detection via `months_active` |
| `payment_reconciliation` | Statement reconciliation with `interest_risk` and `estimated_interest` |
| `monthly_card_summary` | Current statement status per card with utilisation % |

---

## Key Features

**Automated Data Pipeline**
- Gmail API monitors inbox for new statement emails
- PDF attachments extracted using `pdfplumber`
- Gemini AI parses unstructured PDF text into structured transactions
- Duplicate prevention via Gmail message ID

**dbt Transformation Layer**
- 5 mart models transform raw transactions into analytics-ready tables
- `is_anomaly` flag auto-detected using rolling 3-month average
- `interest_risk` and `estimated_interest` computed per statement
- `months_active` per merchant enables recurring subscription detection
- Scheduled via dbt Cloud - triggered on demand via Dashboard refresh button

**Analytics Dashboard**
- Spend anomaly detection - months flagged by dbt as unusually high
- Interest risk alerts - statements where only minimum due was paid
- Shared credit pool utilisation - 4 card groups tracked against combined limit
- Loan amortization schedule with prepayment impact calculator
- AI-generated financial observations powered by Gemini

**Production Architecture**
- 55 FastAPI endpoints - full CRUD plus analytics queries
- Three-tier separation: frontend → API → database
- dbt runs on dbt Cloud, completely separate from API server

## Author

**Sangam Kumar** - Data Analyst at Adani Cement

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/sangam-kumar-datanerd)
[![Portfolio](https://img.shields.io/badge/Portfolio-View-FF6B6B?style=flat)](https://www.datascienceportfol.io/SangamKumar)