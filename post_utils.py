import psycopg2
import datetime

from .post_config import DB_CONNECTION
# from voice_studio_stack.logger.logging_tool import get_logger
# logger = get_logger()

# Initiate postgres connection with db
def get_db_connection():
    return psycopg2.connect(**DB_CONNECTION)

# Store payment details in PostgreSQL
# def store_payment_record(user_id, subscription, status, session_id):
#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute(
#         "INSERT INTO payments (user_id, subscription, status, session_id, timestamp) VALUES (%s, %s, %s, %s, %s)",
#         (user_id, subscription, status, session_id, datetime.datetime.utcnow())
#     )
#     conn.commit()
#     cur.close()
#     conn.close()
#     # logger.info(f"Stored payment record for {user_id}: {subscription} - {status}")
#     print(f"Stored payment record for {user_id}: {subscription} - {status}")
    

# Store razorpay payment details in PostgreSQL
def store_razorpay_record(user_id, subscription, status, order_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT IN_paymentsr_id, subscription, status, order_id, timestamp) VALUES (%s, %s, %s, %s, %s)",
        r_id, subscription, status, order_id, datetime.datetime.utcnow())
    )
    conn.commit()
    cur.close()
    conn.close
    # logger.info(f"Stored payment record for {user_id}: {subscription} - {status}")
    print(f"Stored payment record for {user_id}: {subscription} - {status}")

# def move_razorpay_payment_to_deleted(user_id: str, timestamp: str):
#     conn = get_db_connection()
#     cur = conn.cursor()
#     try:
#         cur.execute("SELECT * FROM rz_payments WHERE user_id = %s", (user_id,))
#         records = cur.fetchall()
        
#         if not records:
#             # logger.info(f"No payment records to archive for user {user_id}")
#             return
        
#         for row in records:
#             cur.execute("""
#                 INSERT INTO rz_payments_deleted 
#                 (user_id, subscription, status, order_id, timestamp, deleted_at)
#                 VALUES (%s, %s, %s, %s, %s, %s)
#             """, (
#                 row[0],  # user_id
#                 row[1],  # subscription
#                 row[2],  # status
#                 row[3],  # order_id
#                 row[4],  # timestamp
#                 timestamp
#             ))

#         # Delete from original
#         cur.execute("DELETE FROM rz_payments WHERE user_id = %s", (user_id,))
#         conn.commit()
#         # logger.info(f"Archived and deleted payment records for user: {user_id}")
#     except Exception as e:
#         conn.rollback()
#         # logger.error(f"Error archiving Razorpay records: {e}")
#         raise
#     finally:
#         cur.close()
#         conn.close()
