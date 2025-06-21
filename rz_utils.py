import os
import razorpay
from fastapi import HTTPException
from dotenv import load_dotenv
load_dotenv()
from voice_studio_stack.iam.keycloak import assign_user_role
from voice_studio_stack.database.postgres import get_db_connection, store_razorpay_record
from voice_studio_stack.database.mongodb import refresh_user_audio_count

# Razorpay client
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_checkout_rz(user_id: str, subscription: str):
    """
    Create Razorpay order. Return order_id and key_id.
    """
    print("subscription in create checkout:", subscription)

    amount_map = {
        "premium": 50000,    # Rs500.00 in paise
        "enterprise": 100000 # Rs1000.00 in paise
    }

    if subscription not in amount_map:
        raise HTTPException(status_code=400, detail="Invalid subscription type.")
    
    amount = amount_map[subscription]
    currency = "INR"
    order_data = {
        "amount": amount,
        "currency": currency}
    try:
        order = razorpay_client.order.create(data=order_data)
        store_razorpay_record(user_id, subscription, "pending", order["id"])
        return {
            "order_id": order["id"],
            "key_id": RAZORPAY_KEY_ID,
            "amount": amount,
            "currency": currency,
            "subscription": subscription
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def pay_verify_rz(user_id: str, 
               subscription: str, 
               razorpay_payment_id: str, 
               razorpay_order_id: str, 
               razorpay_signature: str):
    """
    Verifies Razorpay payment signature and updates the payment record.
    """
    try:
        # Verify payment signature
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

        # Retrieve order details to get subscription info
        # order = razorpay_client.order.fetch(razorpay_order_id)
        # subscription = order["notes"].get("subscription", "free")
        order_id = razorpay_order_id
        assign_user_role(user_id, subscription)
        ### refresh the current role usage count to 0

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE rz_payments SET status = %s WHERE user_id = %s AND order_id = %s",
            ("success", user_id, order_id)
        )
        conn.commit()
        cur.close()
        conn.close()

        ### refresh the current user usage count to 0
        refresh_user_audio_count(user_id)
        return {"message": f"User upgraded to {subscription} role."}

    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Signature verification failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# def has_user_paid_rz(user_id: str, subscription: str) -> bool:
#     """
#     Check if the user already has a 'success' status for the given subscription.
#     """
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor()

#         cur.execute("""
#             SELECT 1 FROM rz_payments
#             WHERE user_id = %s AND subscription = %s AND status = 'success'
#             LIMIT 1
#         """, (user_id, subscription))

#         result = cur.fetchone()
#         cur.close()
#         conn.close()

#         return result is not None

#     except Exception as e:
#         raise RuntimeError(f"? Failed to check existing payment: {str(e)}")