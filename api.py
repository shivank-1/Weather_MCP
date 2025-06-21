from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware

from voice_studio_stack.iam.keycloak import get_user_id_roles, assign_user_role, get_current_user, get_user_id_roles
from voice_studio_stack.database.mongodb import get_user_audio_count, apply_enterprise_coupon, refresh_user_audio_count
from voice_studio_stack.payment.razorpay import create_checkout_rz, pay_verify_rz
from voice_studio_stack.logger.logging_tool import get_logger
logger = get_logger()

# CORS Configuration
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5173/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROLE_LIMITS = {
    "free": 2,
    "premium": 7,       # 2 (free) + 5
    "enterprise": 20    # 2 (free) + 5 (premium) + 13
}

# ENDPOINT: PAYMENT
@app.post("/create-rz-session")
async def create_rz_session(
    user: dict = Depends(get_user_id_roles),
    subscription: str = "premium",
    coupon: str = Query(default=None)
):
    """
    Create checkout session for razorpay payment  or apply valid coupon for upgrade.
    Return session_id and payment_url.
    """
    #timestamp = f"{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}" # UTC timestamp
    print("subscription requested:", subscription)
    if subscription not in ["premium", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid subscription type.")
    user_id = user["user_id"]
    user_roles = user["roles"]
    user_role = next((r for r in ["free", "premium", "enterprise"] if r in user_roles), None)
    if not user_role:
        raise HTTPException(status_code=403, detail="Invalid user role.")
    
    # Handle coupon code
    if coupon == "ENTERPRISE50":
        apply_enterprise_coupon(user_id=user_id, coupon_code=coupon)
        assign_user_role(user_id, "enterprise")
        refresh_user_audio_count(user_id)
        return {"detail": "Coupon applied. You have been upgraded to Enterprise."}
    
    video_count = get_user_audio_count(user_id) # No of total generation counts by the user
    # Check if user has already paid
    if user_role == subscription and video_count < ROLE_LIMITS.get(user_role, 0):
        raise HTTPException(status_code=400, detail=f"You already have an active {subscription} subscription and haven't used your current limit.")
    try:
        return create_checkout_rz(user_id=user_id, subscription=subscription)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint: PAYMENT VERIFICATION
@app.get("/verify-payment-rz")
async def verify_payment_rz(order_id: str, subscription: str, razorpay_payment_id: str, razorpay_signature: str, user: dict = Depends(get_current_user)):
    """
    Verify the payment status of a session id and based on that upgrades the role in KeyCloak (if applicable).
    """
    try:
        user_id = user["sub"]
        return pay_verify_rz(user_id=user_id, 
                             subscription = subscription, 
                             razorpay_payment_id = razorpay_payment_id, 
                             razorpay_order_id = order_id, 
                             razorpay_signature = razorpay_signature)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # public_url = ngrok.connect(8000)  # Expose port 8000
    # print(f"Ngrok tunnel URL: {public_url}")
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)