import hashlib
import hmac
import uuid

from app.config import Config


def create_payment_order(amount_rupees: float, quotation_no: str) -> dict:
    """Create Razorpay order or demo order when keys are not configured."""
    amount_paise = int(round(amount_rupees * 100))

    if Config().razorpay_enabled:
        import razorpay

        client = razorpay.Client(
            auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET)
        )
        order = client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": quotation_no,
                "notes": {"quotation_no": quotation_no},
            }
        )
        return {
            "mode": "razorpay",
            "order_id": order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "key_id": Config.RAZORPAY_KEY_ID,
            "quotation_no": quotation_no,
        }

    return {
        "mode": "demo",
        "order_id": f"demo_{uuid.uuid4().hex[:12]}",
        "amount": amount_paise,
        "currency": "INR",
        "quotation_no": quotation_no,
    }


def verify_payment_signature(
    order_id: str, payment_id: str, signature: str
) -> bool:
    if not Config().razorpay_enabled:
        return payment_id.startswith("pay_demo_")

    body = f"{order_id}|{payment_id}"
    expected = hmac.new(
        Config.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
