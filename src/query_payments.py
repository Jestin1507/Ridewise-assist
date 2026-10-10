from pathlib import Path
import sqlite3

DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "ridewise.db"
)


def get_customer_payments(customer_id):
    connection = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )

    try:
        query = """
            SELECT
                b.booking_id,
                p.payment_id,
                p.payment_type,
                p.amount,
                p.gst_amount,
                p.payment_status,
                p.paid_at
            FROM bookings AS b
            JOIN payments AS p
                ON b.booking_id = p.booking_id
            WHERE b.customer_id = ?
            ORDER BY p.paid_at DESC
        """

        rows = connection.execute(
            query,
            (customer_id.strip(),),
        ).fetchall()

        return rows

    finally:
        connection.close()


if __name__ == "__main__":
    customer_id = input("Enter customer ID: ").strip()

    if not customer_id:
        print("Please enter a customer ID.")
    else:
        try:
            payments = get_customer_payments(customer_id)

            if not payments:
                print("No payment records found.")
            else:
                print(f"\nPayment history for {customer_id}\n")

                total_amount = 0
                total_gst = 0

                for payment in payments:
                    (
                        booking_id,
                        payment_id,
                        payment_type,
                        amount,
                        gst,
                        status,
                        paid_at,
                    ) = payment

                    print(f"Booking: {booking_id}")
                    print(f"Payment ID: {payment_id}")
                    print(f"Type: {payment_type}")
                    print(f"Amount excluding GST: ₹{amount:.2f}")
                    print(f"GST: ₹{gst:.2f}")
                    print(f"Status: {status}")
                    print(f"Date: {paid_at}")
                    print("-" * 35)

                    # Count only successful transactions in the totals.
                    if status == "SUCCESS":
                        total_amount += amount
                        total_gst += gst

                print("\nSuccessful transaction summary")
                print(f"Amount excluding GST: ₹{total_amount:.2f}")
                print(f"GST total: ₹{total_gst:.2f}")
                print(
                    f"Total including GST: "
                    f"₹{total_amount + total_gst:.2f}"
                )

        except (sqlite3.Error, TypeError) as error:
            print(f"Database error: {error}")