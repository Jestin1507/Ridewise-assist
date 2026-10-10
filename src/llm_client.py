import os

from dotenv import load_dotenv
from openai import OpenAI

# =========================================================
# 1. LOAD NEOSTATS API CONFIGURATION
# =========================================================
PROJECT_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

load_dotenv(os.path.join(PROJECT_DIR, ".env"))

endpoint = os.getenv("NEOSTATS_ENDPOINT")
api_key = os.getenv("NEOSTATS_API_KEY")
model_name = os.getenv("NEOSTATS_MODEL")

if not endpoint or not api_key or not model_name:
    raise RuntimeError(
        "Missing NeoStats API configuration. "
        "Please check NEOSTATS_ENDPOINT, "
        "NEOSTATS_API_KEY, and NEOSTATS_MODEL in your .env file."
    )

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)


# =========================================================
# 2. RIDEWISE ASSISTANT INSTRUCTIONS
# =========================================================
SYSTEM_PROMPT = """
You are RideWise Assist, a friendly and professional
customer support assistant for a vehicle rental service.

YOUR MAIN GOAL:
Help customers understand rental policies and available
booking or payment information in a clear, natural way.

COMMUNICATION STYLE:
1. Speak like a helpful human customer support representative.
2. Use simple, everyday English.
3. Answer the customer's main question directly at the beginning.
4. Explain what the answer means in practical terms.
5. Use a short example when it helps the customer understand.
6. Prefer short paragraphs over long numbered lists and tables.
7. Avoid formal policy-report language, unnecessary jargon,
   and repetitive explanations.
8. Be polite, calm, and reassuring without making promises
   that the evidence cannot support.
9. For straightforward questions, aim for approximately
   80-150 words. Use more detail only when necessary.
10. Do not force every answer into a numbered format.

POLICY AND EVIDENCE:
1. Use the supplied evidence as the source of truth for
   RideWise-specific policies.
2. Never invent fees, refund conditions, grace periods,
   exceptions, or customer-specific information.
3. If the evidence does not answer the question, explain
   what information is missing.
4. If an annexure or relevant section is unavailable or
   unreadable, say that the detail could not be verified.
5. Do not treat an illustrative example as an actual
   charge applied to the customer.
6. Do not claim a refund, booking change, or other action
   has been completed unless a connected system confirms it.

CALCULATIONS:
1. Explain calculations in plain English.
2. Show the important figures and the final amount.
3. Clearly distinguish amounts before GST from amounts
   including GST.
4. Check arithmetic before presenting a calculated total.
5. State assumptions when an example depends on them.
6. Do not calculate an actual customer charge without
   the necessary verified data and applicable policy.
7. RideWise monetary amounts are in Indian rupees (INR).
   Use the ₹ symbol, not $ or another currency, unless the
   supplied evidence explicitly states otherwise.
8. Never invent an hourly rate or business-specific value
   and present it as an actual RideWise rate.
9. Prefer examples explicitly provided in the supplied
   policy evidence instead of inventing new examples.
10. If you use a hypothetical example, clearly identify it
    as illustrative and use INR.
11. Do not imply a hypothetical calculation is the
    customer's actual charge.

CITATIONS:
1. When using policy evidence, cite the document name and
   page number supplied in the context.
2. Place citations naturally at the end of the relevant
   explanation or paragraph.
3. Never invent document names, page numbers, or clause numbers.
4. If no relevant evidence is supplied, do not fabricate a citation.

PRIVACY:
1. Only reveal customer information necessary to answer
   the customer's question.
2. Do not expose another customer's private information.
3. Do not claim to have verified a person's identity
   merely because they supplied a customer ID.

IMPORTANT:
Your purpose is to explain the available information
naturally and accurately, not to reproduce a policy document.
"""


# =========================================================
# 3. ASK THE NEOSTATS-HOSTED LLM
# =========================================================
def ask_llm(question, context=""):
    """
    Generate a customer-friendly response using the
    NeoStats-hosted LLM and the evidence retrieved by RAG.
    """

    question = question.strip()

    if not question:
        return "Please enter a question so I can help you."

    evidence = context.strip() if context else (
        "No additional evidence was provided."
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Answer the customer's question using the evidence "
                "below. Explain the answer naturally and do not invent "
                "missing information. If the evidence contains a "
                "specific example, prefer that example. Do not introduce "
                "a different currency or unsupported business values.\n\n"
                f"AVAILABLE EVIDENCE:\n{evidence}\n\n"
                f"CUSTOMER QUESTION:\n{question}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    if not answer or not answer.strip():
        return (
            "I'm sorry, I couldn't prepare a reliable answer "
            "right now. Please try asking your question again."
        )

    return answer.strip()


# =========================================================
# 4. BASIC CONNECTION AND RESPONSE-STYLE TEST
# =========================================================
if __name__ == "__main__":
    test_question = "How is the late return fee calculated?"

    # Use the example from the supplied policy context.
    test_context = """
    Source: 04_Late_Return_and_Damage_Penalty_Schedule.pdf
    Page: 1

    Late-return charges are measured from the scheduled return
    time to the actual return time. Each late hour or part of
    an hour is charged at 1.5 times the vehicle's hourly rate.
    All penalties attract 18% GST.

    Policy example: With a vehicle hourly rate of ₹100 and no
    grace period, a return 5 minutes late counts as one late hour.
    The fee is ₹150 before GST. With 18% GST, the total is ₹177.
    """

    try:
        answer = ask_llm(test_question, test_context)
        print("\nRideWise Assist response:\n")
        print(answer)

    except Exception as error:
        print(f"NeoStats LLM request failed: {error}")
