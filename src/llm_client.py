
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


# =========================================================
# 1. LOAD NEOSTATS API CONFIGURATION
# =========================================================

PROJECT_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

# Load local configuration when running on your computer.
load_dotenv(os.path.join(PROJECT_DIR, ".env"))


def get_config(name):
    """Read configuration from local environment or Streamlit Secrets."""

    # First, check local .env or environment variables.
    value = os.getenv(name)
    if value:
        return value

    # If unavailable, check Streamlit Cloud Secrets.
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return None


endpoint = get_config("NEOSTATS_ENDPOINT")
api_key = get_config("NEOSTATS_API_KEY")
model_name = get_config("NEOSTATS_MODEL")


if not endpoint or not api_key or not model_name:
    missing = []

    if not endpoint:
        missing.append("NEOSTATS_ENDPOINT")
    if not api_key:
        missing.append("NEOSTATS_API_KEY")
    if not model_name:
        missing.append("NEOSTATS_MODEL")

    raise RuntimeError(
        "Missing NeoStats configuration: "
        + ", ".join(missing)
        + ". Check your .env file or Streamlit Cloud Secrets."
    )


# Create the NeoStats API client.
client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
    timeout=30.0,
    max_retries=1,
)


# =========================================================
# 2. RIDEWISE ASSISTANT INSTRUCTIONS
# =========================================================

SYSTEM_PROMPT = """
You are RideWise Assist, a helpful and professional
customer support assistant for an electric vehicle rental service.

Answer the customer's question clearly and naturally.

Use the supplied evidence as the source of truth for
RideWise-specific policies and customer information.

Do not invent fees, refund rules, discounts, booking details,
payment information, or policy exceptions.

If the evidence is insufficient, clearly explain that
the answer could not be verified from the available information.

When policy evidence is provided, cite the document name
and page number supplied in the evidence.

For calculations, show the relevant figures and explain
whether the amount includes GST.

Never present an illustrative example as an actual
customer charge.

Do not claim that a booking change, refund, or other action
has been completed unless a connected system confirms it.

Use Indian rupees (₹) for monetary values unless the
supplied evidence explicitly specifies another currency.

Keep responses concise, friendly, and easy to understand.
"""


# =========================================================
# 3. ASK THE NEOSTATS-HOSTED LLM
# =========================================================

def ask_llm(question, context=""):
    """
    Generate an answer using the NeoStats-hosted LLM
    and the evidence retrieved by the RAG pipeline.
    """

    if not isinstance(question, str) or not question.strip():
        return "Please enter a question so I can help you."

    question = question.strip()

    if isinstance(context, str) and context.strip():
        evidence = context.strip()
    else:
        evidence = "No additional evidence was provided."

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Answer the customer's question using the "
                "available evidence. Do not invent missing facts.\n\n"
                f"AVAILABLE EVIDENCE:\n{evidence}\n\n"
                f"CUSTOMER QUESTION:\n{question}"
            ),
        },
    ]

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
        )

        answer = response.choices[0].message.content

        if not answer or not answer.strip():
            return (
                "I'm sorry, I couldn't prepare a reliable answer "
                "right now. Please try again shortly."
            )

        return answer.strip()

    except Exception as error:
        # Log the error type without exposing credentials.
        print(
            f"NeoStats API request failed: "
            f"{type(error).__name__}"
        )

        # Return a diagnostic that can be seen during testing.
        return (
            "The AI service request failed. "
            f"Error type: {type(error).__name__}. "
            "Please check the application logs and API configuration."
        )


# =========================================================
# 4. BASIC CONNECTION TEST
# =========================================================

if __name__ == "__main__":
    test_question = "How is the late-return fee calculated?"

    test_context = """
    Source: 04_Late_Return_and_Damage_Penalty_Schedule.pdf
    Page: 1

    Each late hour or part of an hour is charged at 1.5 times
    the vehicle's hourly rate. Penalties attract 18% GST.

    Example: If the hourly rate is ₹100, one late hour costs
    ₹150 before GST. GST is ₹27, making the illustrative
    total ₹177.
    """

    print("\nTesting RideWise Assist LLM connection...\n")

    result = ask_llm(test_question, test_context)

    print(result)
