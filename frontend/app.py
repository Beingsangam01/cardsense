import streamlit as st
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="CardSense",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("💳 CardSense")
st.caption("Personal credit card intelligence platform")

st.markdown("---")

st.markdown("""
### 👈 Use the sidebar to navigate

| Page | What you'll find |
|------|-----------------|
| 🏠 Dashboard | Overview, danger zone, due dates |
| 📄 Statements | Upload PDF statements |
| 💸 Payments | Log payments, view history |
| 📈 Insights | Spending analytics |
| 🏦 Loans | EMI tracker, amortization |
| ⚙️ Settings | Scheduler |
""")
