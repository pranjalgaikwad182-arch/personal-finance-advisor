import os
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def build_advisor_prompt(financial_data: dict, user_type: str) -> str:
    """
    Constructs a disciplined, facts-first prompt for Gemini.
    Supplies all deterministic calculations from Python to ensure the AI never does arithmetic.
    """
    income = financial_data.get("income", 0.0)
    expenses = financial_data.get("expenses", 0.0)
    savings = financial_data.get("savings", 0.0)
    savings_rate = financial_data.get("savings_rate", 0.0)
    category_expenses = financial_data.get("category_expenses", {})
    budget_items = financial_data.get("budget_info", {}).get("budget_items") or financial_data.get("budget_info", {}).get("items", [])
    goals = financial_data.get("active_goals", [])

    # Format category breakdown string
    categories_str = "\n".join(
        [f"- {cat}: ₹{amt:,.2f}" for cat, amt in category_expenses.items()]
    ) or "None recorded"

    # Format budget status string
    budgets_str = "\n".join(
        [
            f"- {b['category']}: Budgeted ₹{b['budgeted']:,.2f}, Spent ₹{b['spent']:,.2f} ({b['utilization']}% utilized, Status: {b['status_label']})"
            for b in budget_items
        ]
    ) or "No category budgets configured"

    # Format goals string
    goals_str = "\n".join(
        [
            f"- {g.name}: Target ₹{g.target_amount:,.2f}, Saved ₹{g.current_amount:,.2f} ({g.progress_pct}% complete, Target Date: {g.target_date})"
            for g in goals
        ]
    ) or "No active savings goals recorded"

    prompt = f"""You are a personal finance assistant for an educational budgeting application. 
Analyze the following user's PRE-CALCULATED financial data and provide practical, conservative suggestions.
Do not perform raw arithmetic or invent transactions, numbers, or facts.
Clearly distinguish observed spending patterns from forward-looking recommendations.
Do not recommend specific stocks, crypto, commercial investment schemes, or branded financial products.

USER PROFILE:
- User Situation / Persona: {user_type}

PRE-CALCULATED FINANCIAL SUMMARY:
- Monthly Income: ₹{income:,.2f}
- Monthly Expenses: ₹{expenses:,.2f}
- Net Monthly Savings: ₹{savings:,.2f}
- Savings Rate: {savings_rate}%

RECORDED EXPENSES BY CATEGORY:
{categories_str}

BUDGET LIMITS & UTILIZATION:
{budgets_str}

ACTIVE SAVINGS GOALS:
{goals_str}

REQUIRED OUTPUT FORMAT:
Provide concise, constructive Markdown text organized under these exact section headers:

### 1. Spending Insights
Brief, objective observations on the user's spending patterns this month based strictly on the figures above, tailored to their situation as a {user_type}.

### 2. Overspending & Budget Observations
Specific notes on categories that are exceeding budget, approaching limits, or taking a large percentage of total income.

### 3. Practical Saving Opportunities
2 to 4 actionable, realistic ways this {user_type} can trim discretionary expenses without severe lifestyle disruption.

### 4. Goal & Next Month Action Plan
Prioritized steps for next month, including guidance on building their emergency buffer and keeping their active savings goals on track.

### 5. Summary & Disclaimer
A 2-sentence encouraging wrap-up, concluding with a reminder that this is educational planning assistance and not certified financial advisory."""

    return prompt


def get_rule_based_fallback_insights(financial_data: dict, user_type: str) -> str:
    """
    Intelligent rule-based fallback advisory text generated deterministically in Python
    when Gemini API key is not configured or network call fails.
    Ensures the demo/viva never presents a broken screen.
    """
    income = financial_data.get("income", 0.0)
    expenses = financial_data.get("expenses", 0.0)
    savings = financial_data.get("savings", 0.0)
    savings_rate = financial_data.get("savings_rate", 0.0)
    top_cat = financial_data.get("top_category_name", "None")
    over_budget = financial_data.get("over_budget_count", 0)

    # Determine personalized narrative based on user persona
    if user_type == "Student":
        persona_note = "As a student managing a monthly allowance, keeping discretionary expenses (eating out, entertainment) under check is vital to avoid month-end shortages."
    elif user_type == "Freelancer":
        persona_note = "As a freelancer with variable monthly income, maintaining a 3-6 month emergency runway is your top financial priority to cushion against slow billing cycles."
    elif user_type == "Household Manager":
        persona_note = "Managing household finances requires balancing fixed essentials (rent, utilities, groceries) with long-term family security goals."
    else:
        persona_note = "As a salaried professional, automating fixed savings right after payday helps you reach your financial milestones smoothly."

    return f"""### 1. Spending Insights
- **Overview:** Recorded monthly income of **₹{income:,.2f}** with expenses of **₹{expenses:,.2f}**, generating net savings of **₹{savings:,.2f}** (Savings Rate: **{savings_rate}%**).
- **Top Outflow:** Your highest spending area this month is **{top_cat}**.
- **Persona Context:** {persona_note}

### 2. Overspending & Budget Observations
- Currently, **{over_budget}** categories have exceeded their allocated monthly budget limits.
- {"Your current savings rate is healthy (>20%). Maintaining this pace will accelerate your targets." if savings_rate >= 20 else "Your savings rate is below the recommended 20% benchmark. Trimming discretionary categories will improve financial flexibility."}

### 3. Practical Saving Opportunities
- **Review {top_cat}:** Because {top_cat} accounts for your largest expense, setting a strict weekly cap can yield immediate savings.
- **Audit Recurring Bills:** Review utility bills, subscriptions, and memberships for potential tier downgrades or bundle discounts.
- **The 24-Hour Rule:** Wait 24 hours before making non-essential purchases above ₹1,000 to minimize impulse buying.

### 4. Goal & Next Month Action Plan
- Ensure automatic monthly contributions to your emergency reserve before allocating funds to discretionary spending.
- Set category-specific budget limits for any unbudgeted spending areas.
- Review your monthly statement at the close of the month to evaluate budget adherence.

### 5. Summary & Disclaimer
*Your current financial foundation is clear, and targeted adjustments to your top categories will build sustained savings momentum.*

*Disclaimer: This analysis is generated for educational budgeting and self-management purposes only and does not constitute certified investment or legal financial advice.*"""


def generate_ai_insights(financial_data: dict, user_type: str = "Salaried Professional") -> dict:
    """
    Generates AI-powered financial advisory observations using Google Gemini API.
    Gracefully handles API failures and missing keys with zero application downtime.
    """
    api_key = current_app.config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "").strip()
    model_name = current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash")

    # If no Gemini API key configured, use graceful rule-based fallback
    if not api_key or api_key == "your-gemini-api-key-here":
        fallback_content = get_rule_based_fallback_insights(financial_data, user_type)
        return {
            "source": "rule_engine",
            "is_ai": False,
            "notice": (
                "AI insights are temporarily unavailable. Your financial calculations and reports are still available. "
                "(Set GEMINI_API_KEY in your .env file to enable live Gemini AI integration)."
            ),
            "content": fallback_content,
        }

    try:
        from google import genai

        prompt = build_advisor_prompt(financial_data, user_type)
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        ai_text = response.text if hasattr(response, "text") and response.text else ""
        if not ai_text:
            raise ValueError("Empty response received from Gemini API.")

        return {
            "source": "gemini",
            "is_ai": True,
            "notice": None,
            "content": ai_text,
        }

    except Exception as exc:
        logger.warning("Gemini API call failed (%s). Falling back to rule engine.", exc)
        fallback_content = get_rule_based_fallback_insights(financial_data, user_type)
        return {
            "source": "fallback",
            "is_ai": False,
            "notice": (
                f"AI insights are temporarily unavailable ({exc}). "
                "Your financial calculations and reports are still available."
            ),
            "content": fallback_content,
        }
