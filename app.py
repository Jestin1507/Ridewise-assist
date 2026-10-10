import sys

import sqlite3

from pathlib import Path

import streamlit as st

# ---------------------------------------------------------

# Configuration

# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parent

SRC = ROOT / "src"

DB_PATH = ROOT / "data" / "ridewise.db"

if str(SRC) not in sys.path:

    sys.path.insert(0, str(SRC))

from rag_pipeline import RideWiseRAG

st.set_page_config(

    page_title="RideWise | Support Centre",

    page_icon="🚘",

    layout="wide",

    initial_sidebar_state="expanded",

)

# ---------------------------------------------------------

# Styling

# ---------------------------------------------------------

st.markdown(

    """

    <style>

    @import url('https*\:*//fonts.googleapis.com/css2?family=DM+Sans:wght*\@*400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    .stApp { background: #f5f7fb; color: #17243b; }

    .block-container { max-width: 1250px; padding-top: 1.8rem; padding-bottom: 3rem; }

    section[data-testid="stSidebar"] { background: #fff; border-right: 1px solid #e5eaf1; }

    h1, h2, h3 { color: #17243b !important; letter-spacing: -0.4px; }

    p, label { color: #56647a; }

    /* High-contrast buttons */

    .stButton > button,

    .stFormSubmitButton > button {

        background-color: #ffffff !important;

        color: #17324d !important;

        border: 1px solid #cbd5e1 !important;

        border-radius: 9px !important;

        min-height: 42px;

        font-weight: 600 !important;

    }

    .stButton > button:hover,

    .stFormSubmitButton > button:hover {

        background-color: #e8f4ff !important;

        color: #123047 !important;

        border-color: #0284c7 !important;

    }

    .stButton > button[kind="primary"],

    .stFormSubmitButton > button[kind="primary"] {

        background-color: #087e8b !important;

        color: #ffffff !important;

        border: 1px solid #087e8b !important;

    }

    .stButton > button[kind="primary"]:hover,

    .stFormSubmitButton > button[kind="primary"]:hover {

        background-color: #066570 !important;

        color: #ffffff !important;

    }

    .hero { background: linear-gradient(120deg, #102a43 0%, #14576a 100%); padding: 30px 32px; border-radius: 18px; color: white; margin-bottom: 24px; }

    .hero h1 { color: white !important; font-size: 31px; margin-bottom: 8px; }

    .hero p { color: #dcecf2; margin-bottom: 0; }

    .eyebrow { color: #087e8b; font-size: 11px; font-weight: 700; letter-spacing: 1.7px; text-transform: uppercase; margin-bottom: 10px; }

    .metric-card { background: white; border: 1px solid #e6ebf2; padding: 18px; border-radius: 13px; min-height: 110px; }

    .metric-icon { font-size: 23px; margin-bottom: 8px; }

    .metric-title { color: #17243b; font-weight: 700; font-size: 15px; }

    .metric-sub { color: #758198; font-size: 12px; margin-top: 5px; }

    .side-brand { font-size: 22px; font-weight: 700; color: #102a43; padding-top: 6px; }

    .side-subtitle { color: #758198; font-size: 12px; margin: 4px 0 24px; }

    .chat-user { background: #e5f5f4; padding: 14px 17px; border-radius: 14px 14px 3px 14px; color: #173a40; margin: 12px 0 16px 10%; border: 1px solid #d2eeeb; }

    .chat-label { font-size: 11px; color: #087e8b; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }

    div[data-testid="stForm"] { background: white; border: 1px solid #dce4ee; border-radius: 13px; padding: 12px; }

    hr { border-color: #e6ebf2; }

    </style>

    """,

    unsafe_allow_html=True,

)

# ---------------------------------------------------------

# Session state

# ---------------------------------------------------------

def init_state():

    defaults = {

        "messages": [],

        "customer_id_input": "",

        "customer_lookup_ok": False,

        "customer_lookup_id": "",

        "lookup_message": "",

        "draft_question": "",

        "active_page": "Home",

    }

    for key, value in defaults.items():

        if key not in st.session_state:

            st.session_state[key] = value

def reset_conversation():

    st.session_state.messages = []

    st.session_state.draft_question = ""

    st.session_state.support_question = ""

init_state()

# ---------------------------------------------------------

# Database helpers

# ---------------------------------------------------------

def run_query(sql, params=()):

    if not DB_PATH.exists():

        raise FileNotFoundError(f"Database not found at: {DB_PATH}")

    # Read-only connection: this app does not modify the supplied database.

    uri = DB_PATH.resolve().as_uri() + "?mode=ro"

    connection = sqlite3.connect(uri, uri=True, timeout=10)

    connection.row_factory = sqlite3.Row

    try:

        return [dict(row) for row in connection.execute(sql, params).fetchall()]

    finally:

        connection.close()

def get_customer(customer_id):

    rows = run_query(

        """

        SELECT customer_id, full_name, kyc_status, customer_tier

        FROM customers

        WHERE UPPER(customer_id) = UPPER(?)

        LIMIT 1

        """,

        (customer_id.strip(),),

    )

    return rows[0] if rows else None

def get_bookings(customer_id):

    return run_query(

        """

        SELECT b.booking_id, b.vehicle_id, b.scheduled_start,

               b.scheduled_end, b.actual_return_at, b.booking_status

        FROM bookings AS b

        WHERE UPPER(b.customer_id) = UPPER(?)

        ORDER BY b.booked_at DESC

        LIMIT 50

        """,

        (customer_id.strip(),),

    )

def get_payments(customer_id):

    return run_query(

        """

        SELECT b.booking_id, p.payment_id, p.payment_type,

               p.amount, p.gst_amount, p.payment_method,

               p.payment_status, p.paid_at

        FROM bookings AS b

        JOIN payments AS p ON p.booking_id = b.booking_id

        WHERE UPPER(b.customer_id) = UPPER(?)

        ORDER BY p.paid_at DESC

        LIMIT 100

        """,

        (customer_id.strip(),),

    )

def detect_intent(question):
    q = question.lower()

    policy_priority_words = (
        "late return", "late-return", "late fee", "late-return fee",
        "late return fee", "penalty", "refund policy",
        "cancellation policy", "battery runs out", "damage policy",
        "rental terms", "grace period",
    )
    if any(word in q for word in policy_priority_words):
        return "policy"

    payment_words = (
        "payment", "payments", "paid", "transaction", "transactions",
        "gst", "payment history", "payment status", "total paid",
        "money paid", "my bill", "payment amount",
    )
    booking_words = (
        "booking", "bookings", "reservation", "reservations",
        "booking status", "my trips", "upcoming trip", "scheduled booking",
    )
    policy_words = (
        "policy", "refund", "cancel", "cancellation", "late return",
        "late fee", "penalty", "battery", "damage", "agreement", "terms",
        "ev", "electric vehicle", "grace period", "support number",
        "how is", "what happens",
    )

    payment = any(word in q for word in payment_words)
    booking = any(word in q for word in booking_words)
    policy = any(word in q for word in policy_words)

    if policy and (payment or booking):
        return "combined"
    if payment:
        return "payments"
    if booking:
        return "bookings"
    return "policy"

def format_records(title, records):

    if not records:

        return f"### {title}\n\nNo matching records were found."

    output = [f"### {title}", ""]

    for number, record in enumerate(records, start=1):

        output.append(f"**Record {number}**")

        for key, value in record.items():

            if value is not None:

                label = key.replace("_", " ").title()

                output.append(f"- **{label}:** {value}")

        output.append("")

    return "\n".join(output)

@st.cache_resource

def load_rag():

    return RideWiseRAG()

# ---------------------------------------------------------

# Sidebar

# ---------------------------------------------------------

with st.sidebar:

    st.markdown('<div class="side-brand">🚘 RideWise</div>', unsafe_allow_html=True)

    st.markdown('<div class="side-subtitle">CUSTOMER CARE PORTAL</div>', unsafe_allow_html=True)

    st.markdown("**NAVIGATION**")

    pages = ["Home", "My Bookings", "Payments", "Chat Support"]

    icons = {"Home": "⌂", "My Bookings": "▤", "Payments": "₹", "Chat Support": "✳"}

    for page_name in pages:

        if st.button(

            f"{icons[page_name]}  {page_name}",

            key=f"nav_{page_name}",

            width="stretch",

            type="primary" if st.session_state.active_page == page_name else "secondary",

        ):

            st.session_state.active_page = page_name

            st.rerun()

    st.divider()

    st.markdown("**YOUR PROFILE**")

    st.selectbox("Access mode", ["Customer", "Support Agent"], key="selected_role")

    st.text_input("Customer ID", key="customer_id_input", placeholder="e.g. CUST0001")

    if st.button("Find customer", width="stretch", type="primary"):

        entered = st.session_state.customer_id_input.strip()

        st.session_state.customer_lookup_ok = False

        st.session_state.customer_lookup_id = ""

        if not entered:

            st.session_state.lookup_message = "Enter a customer ID first."

        else:

            try:

                customer = get_customer(entered)

                if customer:

                    st.session_state.customer_lookup_ok = True

                    st.session_state.customer_lookup_id = customer["customer_id"]

                    st.session_state.lookup_message = f"Record found: {customer['customer_id']}"

                else:

                    st.session_state.lookup_message = "Customer ID not found. Please check it."

            except Exception as error:

                print(f"Customer lookup error: {error}")

                st.session_state.lookup_message = "Database lookup failed. Check the terminal for details."

    if st.session_state.lookup_message:

        if st.session_state.customer_lookup_ok:

            st.success(st.session_state.lookup_message)

        else:

            st.warning(st.session_state.lookup_message)

    if st.session_state.customer_lookup_ok:

        st.caption("Demo customer record connected.")

    st.divider()

    if st.button("＋  New conversation", width="stretch"):

        reset_conversation()

        st.session_state.active_page = "Chat Support"

        st.rerun()

    st.caption("RideWise Assist · Hackathon Demo")

    st.caption("Customer ID lookup is not identity verification.")

# ---------------------------------------------------------

# Page content

# ---------------------------------------------------------

page = st.session_state.active_page

if page == "Home":

    st.markdown(

        """

        <div class="hero">

          <div style="font-size:11px;font-weight:700;letter-spacing:1.7px;color:#75ded4;">RIDEWISE SUPPORT CENTRE</div>

          <h1>Your journey, supported.</h1>

          <p>Get help with bookings, payments, rental policies, and electric vehicles.</p>

        </div>

        """,

        unsafe_allow_html=True,

    )

    st.subheader("What would you like help with?")

    st.write("Choose a section below. Your conversation is kept on the separate Chat Support page.")

    c1, c2, c3 = st.columns(3)

    cards = [

        (c1, "🚘", "My Bookings", "View booking details and status"),

        (c2, "₹", "Payments", "Review payment transactions"),

        (c3, "✳", "Chat Support", "Ask questions about policies and EV support"),

    ]

    for col, icon, title, subtitle in cards:

        with col:

            st.markdown(

                f'<div class="metric-card"><div class="metric-icon">{icon}</div>'

                f'<div class="metric-title">{title}</div><div class="metric-sub">{subtitle}</div></div>',

                unsafe_allow_html=True,

            )

            if st.button(f"Open {title}", key=f"open_{title}", width="stretch"):

                st.session_state.active_page = title

                st.rerun()

    st.write("")

    st.subheader("Quick questions")

    quick_actions = [

        ("Late-return fee", "How is the late return fee calculated?"),

        ("EV battery assistance", "What should I do if my EV battery runs out?"),

        ("Cancellation and refunds", "Which cancellation and refund policy applies to my booking?"),

        ("Damage policy", "What does the damage penalty policy say?"),

    ]

    cols = st.columns(2)

    for index, (label, prompt) in enumerate(quick_actions):

        with cols[index % 2]:

            if st.button(label, key=f"quick_{index}", width="stretch"):

                st.session_state.draft_question = prompt

                st.session_state.active_page = "Chat Support"

                st.rerun()

elif page == "My Bookings":

    st.markdown('<div class="eyebrow">YOUR ACCOUNT</div>', unsafe_allow_html=True)

    st.title("My Bookings")

    st.write("View booking records associated with the selected demo customer.")

    if not st.session_state.customer_lookup_ok:

        st.info("Find a customer using the sidebar before viewing demo bookings.")

    else:

        try:

            records = get_bookings(st.session_state.customer_lookup_id)

            if records:

                st.dataframe(records, width="stretch", hide_index=True)

            else:

                st.info("No booking records were found for this customer.")

        except Exception as error:

            print(f"Bookings query error: {error}")

            st.error(f"Unable to load bookings. Exact error: {error}")

elif page == "Payments":

    st.markdown('<div class="eyebrow">YOUR ACCOUNT</div>', unsafe_allow_html=True)

    st.title("Payments & Transactions")

    st.write("Review recorded booking and penalty transactions.")

    if not st.session_state.customer_lookup_ok:

        st.info("Find a customer using the sidebar before viewing demo payments.")

    else:

        try:

            records = get_payments(st.session_state.customer_lookup_id)

            if records:

                st.dataframe(records, width="stretch", hide_index=True)

            else:

                st.info("No payment records were found for this customer.")

        except Exception as error:

            print(f"Payments query error: {error}")

            st.error(f"Unable to load payments. Exact error: {error}")

elif page == "Chat Support":

    st.markdown('<div class="eyebrow">HELP & SUPPORT</div>', unsafe_allow_html=True)

    st.title("Chat Support")

    st.write("Ask about refunds, late-return fees, rental terms, vehicle damage, or EV battery issues.")

    st.caption("Policy answers use the supplied policy documents. Booking and payment answers use the demo database.")

    if st.session_state.messages:

        for message in st.session_state.messages:

            if message["role"] == "user":

                st.markdown(

                    f'<div class="chat-user"><strong>You</strong><br>{message["content"]}</div>',

                    unsafe_allow_html=True,

                )

            else:

                with st.container(border=True):

                    st.markdown('<div class="chat-label">RideWise Support</div>', unsafe_allow_html=True)

                    st.markdown(message["content"])

                    if message.get("sources"):

                        with st.expander("View policy sources"):

                            for source in message["sources"]:

                                st.write(f"{source['source']} - page {source['page']}")

    with st.form("support_message_form", clear_on_submit=True):

        question = st.text_input(

            "Your question",

            key="support_question",

            value=st.session_state.draft_question,

            placeholder="Ask a question about your booking or a policy...",

        )

        send = st.form_submit_button("Send message →", type="primary", width="stretch")

    if send and question.strip():

        question = question.strip()

        st.session_state.draft_question = ""

        st.session_state.messages.append({"role": "user", "content": question})

        try:

            intent = detect_intent(question)

            parts = []

            sources = []

            if intent in ("bookings", "payments", "combined"):

                if not st.session_state.customer_lookup_ok:

                    parts.append(

                        "Please find a demo customer using the sidebar before requesting booking or payment records. "

                        "A customer ID lookup is not identity verification."

                    )

                else:

                    customer_id = st.session_state.customer_lookup_id

                    if intent in ("bookings", "combined"):

                        parts.append(format_records("Booking Records", get_bookings(customer_id)))

                    if intent in ("payments", "combined"):

                        parts.append(format_records("Payment Records", get_payments(customer_id)))

            if intent in ("policy", "combined"):

                with st.spinner("Reviewing the relevant policy documents..."):

                    result = load_rag().answer_question(question)

                parts.append(result.get("answer", "I couldn't find a supported answer in the supplied policies."))

                sources = result.get("sources", [])

            answer = "\n\n".join(part for part in parts if part).strip()

            if not answer:

                answer = "Please rephrase your question and try again."

        except Exception as error:

            print(f"RideWise chat error: {error}")

            answer = "We couldn't process your request right now. Please try again and check the application terminal if the problem continues."

            sources = []

        st.session_state.messages.append(

            {"role": "assistant", "content": answer, "sources": sources}

        )

        st.rerun()

    if st.button("Clear chat history", width="content"):

        reset_conversation()

        st.rerun()

st.markdown(

    '<p style="text-align:center;color:#8a96a8;font-size:11px;margin-top:28px;">'

    'RideWise Assist · AI-generated responses should be checked against official policy and transaction records.'

    '</p>',

    unsafe_allow_html=True,

)
