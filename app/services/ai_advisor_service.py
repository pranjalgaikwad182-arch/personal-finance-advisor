import os
import re
import json
import logging

logger = logging.getLogger(__name__)

# Category tips: recommended budget percentage thresholds for prompt and fallback rules
CATEGORY_TIPS = {
    "rent": "should not exceed 30% of income",
    "food": "under 15%",
    "transport": "within 10%",
    "entertainment": "5–8%",
    "savings": "minimum 20%",
    "utilities": "typically 5–10% of income",
    "healthcare": "around 5–10% of income",
    "shopping": "discretionary, recommended under 10%",
    "other": "miscellaneous spending should stay under 5%",
}

# Recommended numerical benchmark percentages (max recommended portion of income)
RECOMMENDED_BENCHMARKS = {
    "rent": 30.0,
    "food": 15.0,
    "transport": 10.0,
    "entertainment": 8.0,
    "utilities": 8.0,
    "healthcare": 8.0,
    "shopping": 10.0,
    "savings": 20.0,
    "other": 5.0,
}

# Goal descriptions: mappings for common financial goals embedded in prompts
GOAL_DESCRIPTIONS = {
    "emergency_fund": "Building a 3-6 month safety cushion for unforeseen expenses",
    "vacation": "Saving for travel and holiday experiences",
    "gadget_purchase": "Purchasing tech gadgets, laptop, or phone without debt",
    "investment": "Long-term wealth creation, index funds, or mutual funds",
    "general_savings": "Consistent wealth accumulation and financial freedom",
    "debt_payoff": "Aggressive repayment of high-interest loans and credit",
}


def build_prompt(income: float, expenses: dict, goal: str = "emergency_fund") -> str:
    """
    Assembles a structured financial prompt string from income, expense categories,
    and financial goals, instructing Gemini to return strictly valid JSON.
    """
    total_expenses = sum(expenses.values()) if expenses else 0.0
    net_savings = max(0.0, income - total_expenses)
    savings_rate = round((net_savings / income * 100), 2) if income > 0 else 0.0

    goal_key = str(goal).lower().replace(" ", "_").replace("-", "_")
    goal_desc = GOAL_DESCRIPTIONS.get(goal_key, f"Financial milestone: {goal}")

    tips_lines = "\n".join([f"- {cat.capitalize()}: {tip}" for cat, tip in CATEGORY_TIPS.items()])
    expense_lines = "\n".join([f"- {cat.capitalize()}: ₹{float(amt):,.2f}" for cat, amt in expenses.items()])

    prompt = f"""You are a professional AI Personal Finance Advisor.
Analyze the user's financial inputs and produce a customized, realistic budget plan, spending analysis, and actionable saving suggestions in Indian Rupees (₹).

FINANCIAL INPUT DATA:
- Monthly Income: ₹{income:,.2f}
- Recorded Category Expenses:
{expense_lines}
- Total Current Expenses: ₹{total_expenses:,.2f}
- Net Monthly Savings: ₹{net_savings:,.2f} (Savings Rate: {savings_rate}%)
- Primary Financial Goal: {goal} ({goal_desc})

RECOMMENDED BUDGET GUIDELINES:
{tips_lines}

INSTRUCTIONS:
You MUST respond with a strictly valid JSON object and nothing else. No markdown surrounding text or conversational greetings.
The JSON object MUST contain exactly the following four top-level keys:
1. "budget": A dictionary where each key is an expense category name (lowercase, e.g., "rent", "food", "transport", "entertainment", "utilities", "healthcare", "shopping", "other") and the value is an object with:
   - "recommended_amount": number (recommended monthly allocation in ₹)
   - "actual_amount": number (current actual spending in ₹)
   - "percentage_of_income": number (percentage of total income spent, rounded to 1 decimal place)
   - "status": string ("within_budget" or "exceeded")
2. "analysis": An array of objects detailing category health. Each object has:
   - "category": string (e.g. "Rent", "Food")
   - "percentage": number (percentage of total income spent, rounded to 1 decimal place)
   - "status": string ("on track" or "overspending")
   - "message": string (concise 1-2 sentence observation evaluating this spending against healthy benchmarks)
3. "suggestions": An array of 3 to 5 strings. Each string must be a concrete, actionable saving tip specifying exact rupee amounts (₹) to trim or redirect toward their goal ({goal}).
4. "summary": A concise 2-3 sentence monthly financial health summary summarizing total income, total expenses, savings achieved, and encouraging outlook.
"""
    return prompt


def extract_json(text: str) -> dict:
    """
    Robust JSON parser that:
    1. Attempts direct JSON parsing.
    2. Strips markdown code blocks (```json ... ``` or ``` ... ```).
    3. Uses regex fallback to extract raw JSON object {...}.
    """
    if not text:
        raise ValueError("Empty response text from AI.")

    raw = text.strip()

    # Strategy 1: Direct JSON parsing
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown code blocks
    if "```" in raw:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

    # Strategy 3: Regex fallback to find outermost JSON object { ... }
    match = re.search(r"(\{[\s\S]*\})", raw)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    raise ValueError("Failed to extract valid JSON from model response.")


def generate_rule_based_analysis(income: float, expenses: dict, goal: str = "emergency_fund") -> dict:
    """
    Deterministic rule-based fallback advisory engine.
    Computes exact financial metrics, category allocations, spending chips,
    and tailored saving suggestions with specific ₹ amounts.
    Guarantees 100% reliable functionality when Gemini API is unavailable.
    """
    income = float(income)
    total_expenses = sum(float(v) for v in expenses.values())
    net_savings = max(0.0, income - total_expenses)
    savings_rate = round((net_savings / income * 100), 1) if income > 0 else 0.0

    goal_key = str(goal).lower().replace(" ", "_").replace("-", "_")
    goal_desc = GOAL_DESCRIPTIONS.get(goal_key, f"Target: {goal}")

    budget = {}
    analysis = []
    suggestions = []

    # Sort categories by spending to identify top outflow
    sorted_expenses = sorted(expenses.items(), key=lambda x: float(x[1]), reverse=True)
    top_cat = sorted_expenses[0][0] if sorted_expenses else "expenses"

    for cat_name, actual_amt in expenses.items():
        actual_amt = float(actual_amt)
        cat_key = cat_name.lower().strip()
        benchmark_pct = RECOMMENDED_BENCHMARKS.get(cat_key, 10.0)
        recommended_amt = round(income * (benchmark_pct / 100.0), 2)
        pct_of_income = round((actual_amt / income * 100.0), 1) if income > 0 else 0.0

        is_over = actual_amt > recommended_amt
        status_code = "exceeded" if is_over else "within_budget"
        status_label = "overspending" if is_over else "on track"

        budget[cat_key] = {
            "recommended_amount": recommended_amt,
            "actual_amount": actual_amt,
            "percentage_of_income": pct_of_income,
            "status": status_code,
        }

        if is_over:
            excess = actual_amt - recommended_amt
            msg = (
                f"{cat_name.capitalize()} spending (₹{actual_amt:,.0f}) is {pct_of_income}% of income, "
                f"exceeding recommended benchmark of {benchmark_pct}%. Trimming ₹{excess:,.0f} will rebalance your budget."
            )
        else:
            msg = (
                f"{cat_name.capitalize()} spending is well controlled at {pct_of_income}% of income, "
                f"within the recommended {benchmark_pct}% threshold."
            )

        analysis.append({
            "category": cat_name.capitalize(),
            "percentage": pct_of_income,
            "status": status_label,
            "message": msg,
        })

    # Generate actionable suggestions with specific ₹ amounts
    overspending_cats = [c for c in analysis if c["status"] == "overspending"]
    if overspending_cats:
        for item in overspending_cats[:2]:
            cat_k = item["category"].lower()
            rec = budget[cat_k]["recommended_amount"]
            act = budget[cat_k]["actual_amount"]
            diff = act - rec
            suggestions.append(
                f"Reduce discretionary spend in {item['category']} by ₹{diff:,.0f}/month to align with the {RECOMMENDED_BENCHMARKS.get(cat_k, 10)}% guideline."
            )
    else:
        suggestions.append(
            f"Great financial discipline! All categories are currently within healthy benchmarks."
        )

    # Goal suggestion with specific ₹ contribution
    if savings_rate >= 20.0:
        suggested_goal_contrib = round(net_savings * 0.7, 0)
        suggestions.append(
            f"Allocate ₹{suggested_goal_contrib:,.0f} of your ₹{net_savings:,.0f} monthly savings towards your '{goal.replace('_', ' ').title()}' goal."
        )
    else:
        needed = round(income * 0.20 - net_savings, 0)
        suggestions.append(
            f"Boost your monthly savings rate to at least 20% by cutting an extra ₹{max(500.0, needed):,.0f} across dining and entertainment."
        )

    # Audit recurring bills tip
    suggestions.append(
        "Audit recurring digital subscriptions, utility plans, and bundle options to free up an estimated ₹1,000–₹2,500 every month."
    )

    summary = (
        f"During this month, your total income was ₹{income:,.2f} and total expenses were ₹{total_expenses:,.2f}, "
        f"resulting in net savings of ₹{net_savings:,.2f} (savings rate of {savings_rate}%). "
        f"By following the tailored budget allocations, you will steadily achieve your {goal.replace('_', ' ').title()} milestone."
    )

    return {
        "budget": budget,
        "analysis": analysis,
        "suggestions": suggestions,
        "summary": summary,
    }


def analyze_finances_with_gemini(income: float, expenses: dict, goal: str = "emergency_fund") -> dict:
    """
    Invokes the Gemini API (model: gemini-2.0-flash) with build_prompt().
    Parses with extract_json() and validates required keys.
    Falls back gracefully to generate_rule_based_analysis() on any API failure or missing key.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    # Also support standard alternate env var AI_API_KEY
    if not api_key or api_key == "your-gemini-api-key-here":
        api_key = os.getenv("AI_API_KEY", "").strip()

    prompt = build_prompt(income, expenses, goal)

    if api_key and api_key != "your-gemini-api-key-here":
        # 1. Try google.generativeai first
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            if response and hasattr(response, "text") and response.text:
                parsed = extract_json(response.text)
                if all(k in parsed for k in ("budget", "analysis", "suggestions")):
                    if "summary" not in parsed or not parsed["summary"]:
                        parsed["summary"] = (
                            f"During this month, total income was ₹{income:,.2f} and expenses were ₹{sum(expenses.values()):,.2f}, "
                            f"resulting in net savings of ₹{max(0.0, income - sum(expenses.values())):,.2f}."
                        )
                    return parsed
        except Exception as exc1:
            logger.info("google.generativeai call failed (%s), trying google.genai...", exc1)
            # 2. Try google.genai client
            try:
                from google import genai as modern_genai
                client = modern_genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                if response and hasattr(response, "text") and response.text:
                    parsed = extract_json(response.text)
                    if all(k in parsed for k in ("budget", "analysis", "suggestions")):
                        if "summary" not in parsed or not parsed["summary"]:
                            parsed["summary"] = (
                                f"During this month, total income was ₹{income:,.2f} and expenses were ₹{sum(expenses.values()):,.2f}, "
                                f"resulting in net savings of ₹{max(0.0, income - sum(expenses.values())):,.2f}."
                            )
                        return parsed
            except Exception as exc2:
                logger.warning("Gemini API invocation failed (%s). Falling back to rule-based engine.", exc2)

    # Graceful rule-based engine fallback
    return generate_rule_based_analysis(income, expenses, goal)


def generate_product_content(product_info: str, platform: str = "general", tone: str = "professional") -> str:
    """
    Generates promotional/educational content for a financial product or feature.
    Used by /generate endpoint.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY", "").strip()

    prompt = f"""You are a personal finance copywriter. Create promotional or educational content based on the following:
Product/Feature Info: {product_info}
Platform: {platform}
Tone: {tone}

Provide concise, compelling content with a clear call-to-action suitable for personal finance audiences."""

    if api_key and api_key != "your-gemini-api-key-here":
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            if response and hasattr(response, "text") and response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning("Gemini generation failed: %s", e)

    # Fallback content generator
    return (
        f"Introducing {product_info}! Designed with a {tone} approach for {platform}, "
        "this smart personal finance capability helps you take control of your financial future, "
        "curb unnecessary spending, and grow long-term wealth. Start budgeting smarter today!"
    )
