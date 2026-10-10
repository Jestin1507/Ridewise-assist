
from pathlib import Path
import sqlite3

DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "ridewise.db"
)


def get_payment_summary(customer_id, booking_id):
    connection = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )

    try:
        query = """
            SELECT
                p.payment_type,
                p.amount,
                p.gst_amount,
                p.payment_status
            FROM bookings AS b
            JOIN payments AS p
                ON b.booking_id = p.booking_id
            WHERE b.customer_id = ?
              AND b.booking_id = ?
        """

        return connection.execute(
            query,
            (customer_id, booking_id),
        ).fetchall()

    finally:
        connection.close()


def display_summary(customer_id, booking_id):
    payments = get_payment_summary(customer_id, booking_id)

    if not payments:
        print("No matching payment records found.")
        return

    total_including_gst = 0.0

    print(f"\nPayment summary for {booking_id}\n")

    for payment_type, amount, gst, status in payments:
        amount = amount or 0.0
        gst = gst or 0.0

        total = amount + gst

        print(
            f"{payment_type}: ₹{amount:.2f} "
            f"+ GST ₹{gst:.2f} = ₹{total:.2f} "
            f"({status})"
        )

        if status == "SUCCESS":
            total_including_gst += total

    print("-" * 40)
    print(
        "Total of successful transactions, including GST: "
        f"₹{total_including_gst:.2f}"
    )


if __name__ == "__main__":
    customer_id = input("Customer ID: ").strip()
    booking_id = input("Booking ID: ").strip()

    display_summary(customer_id, booking_id)
