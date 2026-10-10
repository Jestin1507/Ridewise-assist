from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ridewise.db"


def get_customer_bookings(customer_id):
    connection = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )

    try:
        query = """
            SELECT
                booking_id,
                vehicle_id,
                scheduled_start,
                scheduled_end,
                booking_status
            FROM bookings
            WHERE customer_id = ?
            ORDER BY scheduled_start DESC
        """

        rows = connection.execute(
            query,
            (customer_id.strip(),),
        ).fetchall()

        return rows

    finally:
        connection.close()


if __name__ == "__main__":
    customer_id = input(
        "Enter a customer ID (e.g. CUST0001): "
    ).strip()

    if not customer_id:
        print("Please enter a customer ID.")
    else:
        try:
            bookings = get_customer_bookings(customer_id)

            if bookings:
                print(f"\nBookings for {customer_id}:\n")

                for booking in bookings:
                    print(booking)

                print(f"\nTotal bookings: {len(bookings)}")
            else:
                print("No bookings found for this customer.")

        except sqlite3.Error as error:
            print(f"Database error: {error}")