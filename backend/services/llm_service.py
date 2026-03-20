from google import genai
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini 
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def extract_transactions_from_text(raw_text: str, bank_name: str) -> dict:


    prompt = f"""
        You are a financial data extraction expert. I will give you raw text extracted from a {bank_name} credit card statement PDF.
        
        Your job is to extract ALL transactions and statement details and return them as valid JSON.
        
        IMPORTANT NOTES FOR INDIAN BANK STATEMENTS:
        - The rupee symbol may appear as "C", "Rs", "INR" or "₹" — treat all of these as Indian Rupees
        - Amounts like "C2.00" mean ₹2.00
        - Amounts like "C-,674.07" or "C-674.07" mean NEGATIVE ₹674.07 (credit balance — bank owes the customer)
        - Commas in numbers are thousand separators e.g. "C1,234.56" means 1234.56
        - If Total Amount Due is negative or zero, it means nothing is owed — set total_amount_due to 0
        - If Due Date is "Nil" or missing, set it to null
        - "PREVIOUS STATEMENT DUES RECEIVED" means previous balance was fully paid
        
        Here is the raw statement text:
        
        {raw_text}
        
        Extract the following and return ONLY valid JSON, no explanation, no markdown, no code blocks:
        
        {{
            "statement_details": {{
                "bank_name": "{bank_name}",
                "card_last_four": "last 4 digits of card number",
                "statement_date": "YYYY-MM-DD format",
                "statement_period_start": "YYYY-MM-DD format or null if not found",
                "statement_period_end": "YYYY-MM-DD format or null if not found",
                "due_date": "YYYY-MM-DD format or null if Nil",
                "total_amount_due": "numeric value only, 0 if negative or nil",
                "minimum_amount_due": "numeric value only",
                "opening_balance": "numeric value only",
                "credit_limit": "numeric value only or null"
            }},
            "transactions": [
                {{
                    "transaction_date": "YYYY-MM-DD format",
                    "transaction_time": "HH:MM:SS 24hr format or null if not available",
                    "merchant": "clean merchant name without location or time",
                    "description": "full original description from statement",
                    "amount": "numeric value only, always positive",
                    "transaction_type": "debit or credit",
                    "category": "one of: Food, Travel, Shopping, Fuel, Entertainment, Healthcare, EMI, Subscription, Utilities, Transfer, Cashback, Other",
                    "is_emi": "yes or no",
                    "is_subscription": "yes or no"
                }}
            ],
            "summary": {{
                "total_transactions": "numeric count",
                "total_debits": "numeric total of all debit amounts",
                "total_credits": "numeric total of all credit amounts"
            }}
        }}
        
        Important rules:
        - All amounts must be numbers only, no currency symbols or commas
        - Dates must be in YYYY-MM-DD format
        - If a value is not found, use null
        - transaction_type is "credit" for payments, cashback, refunds. "debit" for purchases
        - Categorize intelligently: Swiggy/Zomato = Food, Uber/Ola/IRCTC = Travel, Netflix/Spotify = Subscription
        - Return ALL transactions without skipping any
        - Amount should always be a positive number regardless of debit or credit
        - Extract transaction_time from the description if present (e.g. "07:57 PM" → "19:57:00"). Remove time from merchant name
        - statement_period looks like "02 Oct, 2025 - 01 Nov, 2025" — extract start and end dates separately
        - Clean merchant names should not contain location, time, or transaction IDs
        """

    try:
        print("Sending to Gemini API...")
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )
        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
        if response_text.endswith("```"):
            response_text = response_text.rsplit("```", 1)[0]

        response_text = response_text.strip()

        extracted_data = json.loads(response_text)
        print(f"Successfully extracted {len(extracted_data.get('transactions', []))} transactions")
        return extracted_data

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        print(f"Raw response was: {response_text}")
        raise Exception(f"Gemini returned invalid JSON: {str(e)}")

    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        raise e


def generate_insights(transactions_summary: str, cards_summary: str) -> str:

    prompt = f"""
    You are a personal finance advisor analyzing someone's credit card spending in India.
    
    Here is their spending data:
    
    TRANSACTIONS SUMMARY:
    {transactions_summary}
    
    CARDS SUMMARY:
    {cards_summary}
    
    Generate 5 personalized, actionable insights about their spending. Be specific with numbers.
    Focus on:
    1. Biggest spending category and whether it seems high
    2. Any unusual spikes or patterns
    3. Which card is being used most and whether that's optimal
    4. Subscription or EMI obligations
    5. One actionable money-saving tip based on their actual spending
    
    Format each insight as a clear, friendly sentence. Use Indian Rupee (₹) for amounts.
    Return as a JSON array of strings like:
    ["insight 1", "insight 2", "insight 3", "insight 4", "insight 5"]
    
    Return ONLY the JSON array, no explanation.
    """

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )
        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
        if response_text.endswith("```"):
            response_text = response_text.rsplit("```", 1)[0]

        insights = json.loads(response_text.strip())
        return insights

    except Exception as e:
        print(f"Insights generation error: {str(e)}")
        return ["Unable to generate insights at this time. Please try again."]


def explain_anomaly(card_name: str, current_amount: float, average_amount: float, transactions: list) -> str:


    prompt = f"""
    A credit card bill for {card_name} is unusually high.
    Current bill: ₹{current_amount}
    3-month average: ₹{average_amount}
    Difference: ₹{current_amount - average_amount} higher than usual ({round((current_amount - average_amount) / average_amount * 100)}% increase)
    
    Top transactions this month:
    {json.dumps(transactions[:10], indent=2)}
    
    In 2-3 sentences, explain in simple friendly language why this bill might be high,
    referencing specific transactions. Be helpful, not alarming.
    Return only the explanation text, no JSON.
    """

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Bill is ₹{current_amount - average_amount:.0f} higher than your usual average."