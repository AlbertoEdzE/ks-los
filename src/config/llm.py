from langchain_ollama import ChatOllama
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from langchain_core.messages import AIMessage
import os
import re
import json
import urllib.request
import urllib.error

# Default to Qwen3 latest unless overridden
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def is_ollama_available(timeout_s: float = 1.5) -> bool:
    base = (OLLAMA_BASE_URL or "").rstrip("/")
    if not base:
        return False
    try:
        req = urllib.request.Request(f"{base}/api/version", method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return 200 <= int(getattr(resp, "status", 0) or 0) < 300
    except (urllib.error.URLError, ValueError):
        return False

class _TestLLM:
    def __init__(self, tools=None, temperature: float = 0.7):
        self._tools = tools or []
        self._temperature = temperature

    def bind_tools(self, tools):
        return _TestLLM(tools=tools, temperature=self._temperature)

    def invoke(self, messages):
        system_content = ""
        for m in messages:
            if m.__class__.__name__ == "SystemMessage":
                system_content = m.content or ""
                break

        last_user = ""
        all_user: list[str] = []
        for m in reversed(messages):
            if m.__class__.__name__ == "HumanMessage":
                last_user = m.content or ""
                break
        for m in messages:
            if m.__class__.__name__ == "HumanMessage" and isinstance(getattr(m, "content", None), str):
                all_user.append(m.content)
        combined_user = "\n".join([t for t in all_user if t.strip()])

        if "Credit Risk Officer" in system_content or '"risk_score"' in system_content:
            return AIMessage(content='{"decision":"MANUAL_REVIEW","risk_score":50,"reasoning":"Test mode response."}')

        if "Expert Financial Advisor" in system_content:
            return AIMessage(content="Test mode advisory response.")

        if "You are LoanAssist" in system_content:
            lower = combined_user.lower()
            purpose = None
            if any(k in lower for k in ["consolidate", "debt consolidation"]):
                purpose = "Debt consolidation"
            elif any(k in lower for k in ["home", "house", "mortgage", "property", "apartment", "flat"]):
                purpose = "Home purchase"
            elif any(k in lower for k in ["car", "auto", "vehicle"]):
                purpose = "Car purchase"

            income = None
            m_income = re.search(r"\b(income|salary)\b[^\d]{0,20}(\d{2,9})", lower)
            if m_income:
                income = m_income.group(2)
            else:
                m_income2 = re.search(r"(\d{2,9})\s*(usd|mxn|inr)?\s*/\s*month", lower)
                if m_income2:
                    income = m_income2.group(1)

            loan_amount = None
            m_amt = re.search(r"\b(loan\s*amount|amount)\b[^\d]{0,20}(\d{2,9})", lower)
            if m_amt:
                loan_amount = m_amt.group(2)
            else:
                m_prop = re.search(r"\b(house|home|property|apartment|flat)\b[^\d]{0,40}(\d{2,9})", lower)
                if m_prop:
                    loan_amount = m_prop.group(2)

            tenure = None
            m_years = re.search(r"\b(\d{1,2})\s*(years|year)\b", lower)
            if m_years:
                tenure = f"{m_years.group(1)} years"
            else:
                m_months = re.search(r"\b(\d{1,3})\s*(months|month)\b", lower)
                if m_months:
                    tenure = f"{m_months.group(1)} months"

            employment = None
            if any(k in lower for k in ["salaried", "employed", "full-time", "full time"]):
                employment = "Salaried"
            elif any(k in lower for k in ["self-employed", "self employed", "freelance", "contractor", "business owner"]):
                employment = "Self-employed"

            debts = None
            if any(k in lower for k in ["no debts", "no debt", "no obligations"]):
                debts = "0"

            credit = None
            m_credit = re.search(r"\b(credit\s*score|cibil)\b[^\d]{0,20}(\d{3})", lower)
            if m_credit:
                credit = m_credit.group(2)
            elif any(k in lower for k in ["dont know my credit", "don't know my credit", "unknown credit", "no idea my credit"]):
                credit = "unknown"

            seriousness = 40
            fit = 55
            if purpose and (income or loan_amount):
                seriousness = 70
            if income and loan_amount:
                fit = 75

            next_angle = "Confirm repayment tenure and down payment to refine options."
            if not loan_amount:
                assistant_text = "Understood. What’s the approximate property price (or your target budget) and your expected down payment?"
            elif not income:
                assistant_text = "Understood. What’s your approximate monthly income (and currency), and do you have any existing monthly obligations?"
            else:
                assistant_text = "Thanks — based on what you’ve shared, here are two sensible paths. Tell me whether you prefer the lowest monthly payment or the lowest total interest."

            product_type = "home_loan" if purpose == "Home purchase" else "personal_loan"
            loan_recommendations = [
                {
                    "name": "Standard Home Purchase Loan" if product_type == "home_loan" else "Standard Personal Loan",
                    "type": product_type,
                    "estimatedRate": "Varies",
                    "estimatedEmi": "TBD",
                    "tenure": tenure or "Flexible",
                    "totalInterest": "TBD",
                    "approvalSpeed": "Standard",
                    "pros": ["Simple structure", "Flexible repayment options"],
                    "cons": ["Rate depends on profile"],
                    "recommendation": "A good baseline option while we finalize your exact terms.",
                }
            ]

            final_recommendation = None
            if purpose and income and loan_amount and tenure:
                final_recommendation = {
                    "name": loan_recommendations[0]["name"],
                    "type": loan_recommendations[0]["type"],
                    "tenure": loan_recommendations[0]["tenure"],
                    "reason": "Matches your goal, income, and preferred tenure based on the current information.",
                }

            income_intent = int(income) if isinstance(income, str) and income.isdigit() else income
            amount_intent = int(loan_amount) if isinstance(loan_amount, str) and loan_amount.isdigit() else loan_amount
            intent_obj = {
                "purpose": purpose,
                "urgency": None,
                "affordability": None,
                "monthlyIncome": income_intent,
                "existingDebts": debts,
                "loanAmount": amount_intent,
                "preferredTenure": tenure,
                "collateralAvailable": None,
                "employmentType": employment,
                "creditHistory": credit,
                "recentDelinquencies12m": None,
                "seriousnessScore": seriousness,
                "fitScore": fit,
                "nextConversationAngle": next_angle,
            }

            parts = [
                assistant_text,
                f"<loan_recommendations>{json.dumps(loan_recommendations)}</loan_recommendations>",
                f"<intent_analysis>{json.dumps(intent_obj)}</intent_analysis>",
            ]
            if final_recommendation is not None:
                parts.append(f"<final_recommendation>{json.dumps(final_recommendation)}</final_recommendation>")
            return AIMessage(content="\n".join(parts))

        age = None
        territory = None
        m_age = re.search(r"(\d{2})\s*year", last_user, flags=re.IGNORECASE)
        if m_age:
            try:
                age = int(m_age.group(1))
            except Exception:
                age = None

        m_terr = re.search(r"\(([A-Z]{2})\)", last_user)
        if m_terr:
            territory = m_terr.group(1)

        if age is not None and territory is not None:
            tool_calls = [
                {
                    "id": "call_generate_profile",
                    "type": "tool_call",
                    "name": "generate_credit_profile",
                    "args": {"age": age, "territory": territory},
                }
            ]
            return AIMessage(content="", additional_kwargs={"tool_calls": tool_calls}, tool_calls=tool_calls)

        return AIMessage(content="Journey Coach (test mode).")


def get_llm(temperature: float = 0.7, model: str | None = None):
    """
    Returns a configured ChatOllama instance.
    """
    if os.getenv("PYTEST_CURRENT_TEST") or str(os.getenv("LLM_TEST_MODE", "")).strip() in {"1", "true", "yes"}:
        return _TestLLM(temperature=temperature)
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=(model or MODEL_NAME),
        temperature=temperature,
        callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]),
        keep_alive="5m"
    )
