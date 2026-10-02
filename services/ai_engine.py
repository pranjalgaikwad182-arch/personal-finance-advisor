import os
import re
import logging
from datetime import date
from flask import current_app
from models import db, User, Income, Expense, Budget, SavingsGoal
from services.financial_analyzer import (
    calculate_total_income,
    calculate_total_expenses,
    calculate_savings,
    calculate_savings_rate,
    get_expenses_by_category,
    get_budget_status,
    get_dashboard_summary,
    get_top_expense_categories,
)
from services.budget_generator import generate_recommended_budgets

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

    categories_str = "\n".join(
        [f"- {cat}: ₹{amt:,.2f}" for cat, amt in category_expenses.items()]
    ) or "None recorded"

    budgets_str = "\n".join(
        [
            f"- {b['category']}: Budgeted ₹{b['budgeted']:,.2f}, Spent ₹{b['spent']:,.2f} ({b['utilization']}% utilized, Status: {b['status_label']})"
            for b in budget_items
        ]
    ) or "No category budgets configured"

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
    """
    income = financial_data.get("income", 0.0)
    expenses = financial_data.get("expenses", 0.0)
    savings = financial_data.get("savings", 0.0)
    savings_rate = financial_data.get("savings_rate", 0.0)
    top_cat = financial_data.get("top_category_name", "None")
    over_budget = financial_data.get("over_budget_count", 0)

    persona_tips = {
        "Student": "Prioritize essential education materials, affordable meal options, and public transport passes. Avoid discretionary impulsiveness on online deliveries.",
        "Salaried Professional": "Automate at least 20% of your salary into a high-yield emergency savings fund before planning discretionary spending for the month.",
        "Freelancer": "Maintain a 6-to-9 month emergency buffer to absorb irregular client payment cycles, and set aside 25% of every invoice for taxes and health coverage.",
        "Household Manager": "Audit recurrent grocery and utility spending, leverage bulk-buying discounts for pantry essentials, and establish dedicated buffers for seasonal healthcare or school fees.",
    }
    advice_tip = persona_tips.get(user_type, persona_tips["Salaried Professional"])

    savings_assessment = (
        f"You maintained a strong savings rate of **{savings_rate}%**, comfortably exceeding the 20% benchmark."
        if savings_rate >= 20.0
        else f"Your savings rate is currently **{savings_rate}%**. You have opportunity to strengthen this towards 20% by curbing discretionary outgo."
        if savings_rate > 0
        else f"Warning: You operated at a **deficit of ₹{abs(savings):,.2f}** this month. Expenses exceeded income."
    )

    budget_assessment = (
        f"All your configured category budgets are within limits."
        if over_budget == 0
        else f"You have **{over_budget} category limit(s) exceeded** this period. Review discretionary outlays immediately."
    )

    return f"""### 1. Spending Insights
You recorded a monthly income of **₹{income:,.2f}** and total expenses of **₹{expenses:,.2f}**, leaving **₹{savings:,.2f}** in net savings.
Your single highest expense category was **{top_cat}**. As a **{user_type}**, {advice_tip}

### 2. Overspending & Budget Observations
{budget_assessment}
Tracking your expenses on a weekly basis ensures high-volume categories like {top_cat} do not drain your monthly liquidity before pay cycle closure.

### 3. Practical Saving Opportunities
- **Evaluate Discretionary Purchases:** Review non-essential subscriptions and entertainment spending.
- **Set Realistic Category Caps:** If recurring categories like {top_cat} regularly approach limits, consider generating an automated balanced budget.
- **Automate First:** Transfer your target monthly savings immediately upon receiving income rather than saving whatever remains at month-end.

### 4. Goal & Next Month Action Plan
- Ensure your emergency liquidity fund has at least 3-6 months of essential expenses covered.
- Maintain consistent contributions to your active savings goals to keep deadlines on track.
- Re-evaluate monthly limits at the start of each month using the intelligent Budget Generator.

### 5. Summary & Educational Disclaimer
*Consistent tracking is the foundation of lasting financial health. Small, steady adjustments create significant long-term safety margins.*
*(Notice: This automated report is generated by the local rule-based advisory engine for educational budgeting purposes and does not constitute certified financial or investment advice.)*"""


def generate_ai_insights(financial_data: dict, user_type: str) -> dict:
    """
    Orchestrates AI advisory response using Google Gemini if available,
    gracefully falling back to the deterministic local rule engine if not.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY")

    if not api_key:
        return {
            "content": get_rule_based_fallback_insights(financial_data, user_type),
            "is_ai": False,
            "notice": "Operating on local rule-based financial engine. (Set GEMINI_API_KEY or AI_API_KEY in .env for live Gemini 2.0 analysis).",
        }

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = build_advisor_prompt(financial_data, user_type)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        if response and response.text:
            return {
                "content": response.text,
                "is_ai": True,
                "notice": None,
            }
        else:
            raise ValueError("Empty response received from Gemini API.")

    except Exception as exc:
        logger.warning("Gemini AI API call failed: %s. Using rule-based fallback.", exc)
        return {
            "content": get_rule_based_fallback_insights(financial_data, user_type),
            "is_ai": False,
            "notice": f"AI service temporarily unavailable ({type(exc).__name__}). Displaying local rule-based analysis.",
        }


def answer_financial_query(user_id: int, query: str, month: int = None, year: int = None) -> dict:
    """
    Answers natural language questions about the user's finances in chat interface.
    Works either with Gemini AI grounded on user data OR local rule-based engine.
    """
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    user = db.session.get(User, user_id)
    user_type = user.user_type if user else "Salaried Professional"

    summary = get_dashboard_summary(user_id, target_month, target_year)
    income = summary["income"]
    expenses = summary["expenses"]
    savings = summary["savings"]
    savings_rate = summary["savings_rate"]
    top_cat_name = summary["top_category_name"]
    top_cat_amt = summary["top_category_amount"]
    category_expenses = summary["category_expenses"]
    budget_info = summary["budget_info"]
    over_budget_count = budget_info["over_budget_count"]
    remaining_budget = budget_info["remaining_budget"]
    active_goals = summary["active_goals"]

    cleaned_query = query.strip().lower()

    # Rule-based query matching for fast, accurate, transparent answers:
    
    # 1. "How much did I spend this month?" / spending total
    if any(k in cleaned_query for k in ["how much did i spend", "total spend", "total expenses", "how much spent", "expenses this month"]):
        if expenses == 0:
            answer = f"You haven't recorded any expenses yet for {today.strftime('%B %Y')}."
        else:
            top_info = f" Your biggest expenditure was **{top_cat_name}** at ₹{top_cat_amt:,.2f}." if top_cat_name != "None" else ""
            answer = (
                f"You have spent **₹{expenses:,.2f}** in {today.strftime('%B %Y')} across {len(category_expenses)} categories.{top_info}\n\n"
                f"With a monthly income of ₹{income:,.2f}, your current net savings are **₹{savings:,.2f}** ({savings_rate}% savings rate)."
            )
        return {"answer": answer, "mode": "rule_based"}

    # 2. "Where am I overspending?" / overspending categories
    if any(k in cleaned_query for k in ["overspend", "over spending", "exceeding budget", "where am i spending too much"]):
        over_items = [b for b in budget_info.get("budget_items", []) if b["status"] == "exceeded"]
        approaching_items = [b for b in budget_info.get("budget_items", []) if b["status"] == "approaching"]

        if over_items:
            details = "\n".join([f"- **{b['category']}**: Spent ₹{b['spent']:,.2f} vs Budget of ₹{b['budgeted']:,.2f} ({b['utilization']}% utilized)" for b in over_items])
            answer = f"You are currently exceeding your budget in **{len(over_items)} category(ies)**:\n\n{details}\n\n"
            if approaching_items:
                app_details = ", ".join([b['category'] for b in approaching_items])
                answer += f"Additionally, you are close to the limit in: **{app_details}**."
        elif approaching_items:
            app_details = "\n".join([f"- **{b['category']}**: Spent ₹{b['spent']:,.2f} of ₹{b['budgeted']:,.2f} ({b['utilization']}%)" for b in approaching_items])
            answer = f"Great news! You have not exceeded any budget limits yet, but you are approaching limits in:\n\n{app_details}"
        else:
            if top_cat_amt > 0:
                answer = f"You are within all your configured category budgets! Your largest expenditure so far is **{top_cat_name}** at ₹{top_cat_amt:,.2f}."
            else:
                answer = "No overspending detected. All your recorded categories are currently within limits."
        return {"answer": answer, "mode": "rule_based"}

    # 3. "How much can I save?" / potential savings
    if any(k in cleaned_query for k in ["how much can i save", "saving capacity", "potential savings", "how much to save"]):
        benchmark_savings = round(income * 0.20, 2)
        optimal_savings = round(income * 0.30, 2)
        if income > 0:
            answer = (
                f"Based on your current monthly income of **₹{income:,.2f}**:\n\n"
                f"- **Standard 20% Target:** ₹{benchmark_savings:,.2f} per month\n"
                f"- **Aggressive 30% Target:** ₹{optimal_savings:,.2f} per month\n\n"
                f"You have currently saved **₹{savings:,.2f}** this month ({savings_rate}%). "
                f"To hit the 20% target (₹{benchmark_savings:,.2f}), "
                f"{'you have already reached your goal! Keep it up.' if savings >= benchmark_savings else f'you need to save an additional ₹{(benchmark_savings - savings):,.2f} by cutting discretionary items like Food dining and Shopping.'}"
            )
        else:
            answer = "Add your monthly income entries first to calculate your exact savings potential."
        return {"answer": answer, "mode": "rule_based"}

    # 4. "Give me a budget for next month" / budget recommendation
    if any(k in cleaned_query for k in ["give me a budget", "budget for next month", "recommended budget", "suggest a budget", "plan next month"]):
        rec_data = generate_recommended_budgets(user_id, target_month, target_year)
        recs = rec_data["recommendations"][:5]
        details = "\n".join([f"- **{r['category']}**: ₹{r['recommended_amount']:,.0f} ({r['rationale']})" for r in recs])
        answer = (
            f"Here is a recommended monthly budget tailored for a **{user_type}** with an income of **₹{rec_data['income']:,.0f}** "
            f"(targeting {rec_data['savings_target_pct']}% / ₹{rec_data['target_savings_amount']:,.0f} in savings):\n\n"
            f"**Top Recommended Allocations:**\n{details}\n\n"
            f"You can apply and customize these directly from the **Budgets** page with one click!"
        )
        return {"answer": answer, "mode": "rule_based"}

    # 5. "Which category costs me the most?" / highest spending
    if any(k in cleaned_query for k in ["category costs me the most", "highest spending", "biggest expense", "most expensive category", "top category"]):
        if top_cat_name != "None" and top_cat_amt > 0:
            cat_pct = round((top_cat_amt / expenses * 100), 1) if expenses > 0 else 0
            inc_pct = round((top_cat_amt / income * 100), 1) if income > 0 else 0
            answer = (
                f"Your highest spending category is **{top_cat_name}** at **₹{top_cat_amt:,.2f}**.\n\n"
                f"- This accounts for **{cat_pct}%** of your total monthly expenses.\n"
                f"- It consumes **{inc_pct}%** of your monthly income."
            )
        else:
            answer = "You haven't recorded any expenses yet to determine your top category."
        return {"answer": answer, "mode": "rule_based"}

    # 6. "How can I reduce my expenses?" / cost cutting advice
    if any(k in cleaned_query for k in ["reduce my expenses", "cut expenses", "lower spending", "spend less", "save money"]):
        discretionary = []
        for cat in ["Food", "Entertainment", "Shopping", "Other"]:
            if cat in category_expenses and category_expenses[cat] > 0:
                discretionary.append(f"**{cat}** (₹{category_expenses[cat]:,.2f})")
        disc_str = ", ".join(discretionary) if discretionary else "discretionary categories"
        answer = (
            f"As a **{user_type}**, here are practical strategies to reduce your monthly expenses:\n\n"
            f"1. **Audit Flexible Outlays:** You currently spend on {disc_str}. Trimming 15-20% from dining out and impulsive shopping can free up cash immediately.\n"
            f"2. **Implement the 48-Hour Rule:** Wait 48 hours before non-essential purchases above ₹1,000 to prevent impulsive buying.\n"
            f"3. **Track Utility & Subscription Drain:** Cancel unused streaming subscriptions or gyms you haven't visited this month.\n"
            f"4. **Adopt 50/30/20 Budgeting:** Keep Needs <= 50%, Wants <= 30%, and direct 20% into savings right on payday."
        )
        return {"answer": answer, "mode": "rule_based"}

    # 7. "How much have I saved?" / savings status
    if any(k in cleaned_query for k in ["how much have i saved", "my savings", "total saved", "savings progress"]):
        goal_text = ""
        if active_goals:
            goal_details = "\n".join([f"- **{g.name}**: ₹{g.current_amount:,.2f} of ₹{g.target_amount:,.2f} ({g.progress_pct}%)" for g in active_goals])
            goal_text = f"\n\n**Active Savings Goals Progress:**\n{goal_details}"

        answer = (
            f"For {today.strftime('%B %Y')}, your net monthly savings are **₹{savings:,.2f}** "
            f"({savings_rate}% of your income of ₹{income:,.2f}).{goal_text}"
        )
        return {"answer": answer, "mode": "rule_based"}

    # 8. "Am I within my budget?" / budget adherence
    if any(k in cleaned_query for k in ["within my budget", "am i on budget", "budget status", "how is my budget"]):
        total_b = budget_info["total_budgeted"]
        spent_b = budget_info["total_spent_budgeted"]
        rem = budget_info["remaining_budget"]
        util = budget_info["overall_utilization"]

        if total_b == 0:
            answer = "You haven't set any category budgets yet for this month. Head to the **Budgets** section to set spending limits or auto-generate a plan!"
        elif over_budget_count > 0:
            answer = (
                f"You have budgeted ₹{total_b:,.2f} and spent ₹{spent_b:,.2f} ({util}% overall).\n\n"
                f"However, you have **exceeded the limit in {over_budget_count} category(ies)**. "
                f"Remaining total budget buffer across other categories is **₹{rem:,.2f}**."
            )
        else:
            answer = (
                f"Yes! You are currently **within your overall budget**.\n\n"
                f"- Total Budgeted: ₹{total_b:,.2f}\n"
                f"- Total Spent on Budgeted Items: ₹{spent_b:,.2f} ({util}% utilized)\n"
                f"- Remaining Buffer: **₹{rem:,.2f}**"
            )
        return {"answer": answer, "mode": "rule_based"}

    # Fallback to AI API if available, otherwise general helpful guidance
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = (
                f"You are a helpful personal finance advisor bot. The user's role is {user_type}. "
                f"Their pre-calculated financial data for this month is: "
                f"Income: ₹{income:,.2f}, Expenses: ₹{expenses:,.2f}, Net Savings: ₹{savings:,.2f}, "
                f"Savings Rate: {savings_rate}%, Top expense category: {top_cat_name} (₹{top_cat_amt:,.2f}), "
                f"Budgeted: ₹{budget_info['total_budgeted']:,.2f}, Remaining Budget: ₹{remaining_budget:,.2f}, "
                f"Over-budget categories count: {over_budget_count}. "
                f"User asked: '{query}'. "
                f"Answer concisely, realistically, and conservatively in 2 to 4 sentences in markdown. "
                f"Ground your numbers strictly on their provided data without hallucinating figures. "
                f"Do not give risky investment advice."
            )
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            if res and res.text:
                return {"answer": res.text, "mode": "gemini_ai"}
        except Exception as exc:
            logger.warning("Gemini chat fallback: %s", exc)

    # General contextual fallback
    return {
        "answer": (
            f"Here is your current snapshot: Monthly income is **₹{income:,.2f}**, "
            f"expenses are **₹{expenses:,.2f}**, and net savings are **₹{savings:,.2f}** ({savings_rate}%). "
            f"Your highest expenditure is **{top_cat_name}** at ₹{top_cat_amt:,.2f}. "
            f"Try asking specific questions like *'How much did I spend this month?'*, *'Where am I overspending?'*, or *'Give me a budget for next month.'*"
        ),
        "mode": "rule_based",
    }
