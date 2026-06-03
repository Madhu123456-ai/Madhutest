import json

from flask import Blueprint, jsonify, request, session
from flask_login import login_required

from app.config import Config
from app.models import (
    get_quotation,
    get_tree,
    list_quotations,
    save_customer,
    save_quotation,
    search_trees,
    set_quotation_pdf,
    update_quotation_status,
)
from app.services.payment_service import create_payment_order, verify_payment_signature
from app.services.pdf_service import generate_quotation_pdf

api_bp = Blueprint("api", __name__)


def _cart():
    return session.setdefault("cart", [])


def _calc_totals(items, charges=None):
    charges = charges or {}
    subtotal = sum(float(i.get("rate", i["price"])) * i["qty"] for i in items)
    gst = round(subtotal * Config.GST_RATE / 100, 2)
    labour_charge = round(float(charges.get("labour_charge", 0) or 0), 2)
    transport_charge = round(float(charges.get("transport_charge", 0) or 0), 2)
    discount_amount = round(float(charges.get("discount_amount", 0) or 0), 2)
    total = round(subtotal + gst + labour_charge + transport_charge - discount_amount, 2)
    total = max(total, 0.0)
    return subtotal, gst, labour_charge, transport_charge, discount_amount, total


@api_bp.route("/trees/search")
@login_required
def trees_search():
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return jsonify([])
    return jsonify(search_trees(q))


@api_bp.route("/cart", methods=["GET"])
@login_required
def get_cart():
    cart = _cart()
    if cart:
        subtotal, gst, labour, transport, discount, total = _calc_totals(cart)
    else:
        subtotal, gst, labour, transport, discount, total = (0, 0, 0, 0, 0, 0)
    return jsonify(
        {
            "items": cart,
            "subtotal": subtotal,
            "gst": gst,
            "labour_charge": labour,
            "transport_charge": transport,
            "discount_amount": discount,
            "total": total,
        }
    )


@api_bp.route("/cart/add", methods=["POST"])
@login_required
def cart_add():
    data = request.get_json() or {}
    tree_id = data.get("tree_id")
    tree = get_tree(int(tree_id)) if tree_id else None
    if not tree:
        return jsonify({"error": "Tree not found"}), 404

    cart = _cart()
    for item in cart:
        if item["id"] == tree["id"]:
            item["qty"] += 1
            session.modified = True
            return jsonify({"items": cart, "message": f"{tree['name']} quantity updated"})

    cart.append(
        {
            "id": tree["id"],
            "name": tree["name"],
            "scientific": tree.get("scientific", ""),
            "price": float(tree["price"]),
            "rate": float(tree["price"]),
            "qty": 1,
            "height": "",
            "spacing": "",
            "remarks": "",
        }
    )
    session.modified = True
    return jsonify({"items": cart, "message": f"{tree['name']} added to cart"})


@api_bp.route("/cart/update", methods=["POST"])
@login_required
def cart_update():
    data = request.get_json() or {}
    tree_id = int(data.get("tree_id", 0))
    qty = max(1, int(data.get("qty", 1)))
    cart = _cart()
    for item in cart:
        if item["id"] == tree_id:
            item["qty"] = qty
            if "height" in data:
                item["height"] = str(data.get("height", ""))
            if "spacing" in data:
                item["spacing"] = str(data.get("spacing", ""))
            if "remarks" in data:
                item["remarks"] = str(data.get("remarks", ""))
            if "rate" in data:
                item["rate"] = max(0, float(data.get("rate", item.get("price", 0)) or 0))
            break
    session.modified = True
    subtotal, gst, labour, transport, discount, total = _calc_totals(cart)
    return jsonify(
        {
            "items": cart,
            "subtotal": subtotal,
            "gst": gst,
            "labour_charge": labour,
            "transport_charge": transport,
            "discount_amount": discount,
            "total": total,
        }
    )


@api_bp.route("/cart/remove", methods=["POST"])
@login_required
def cart_remove():
    data = request.get_json() or {}
    tree_id = int(data.get("tree_id", 0))
    cart = [i for i in _cart() if i["id"] != tree_id]
    session["cart"] = cart
    session.modified = True
    if cart:
        subtotal, gst, labour, transport, discount, total = _calc_totals(cart)
    else:
        subtotal, gst, labour, transport, discount, total = (0, 0, 0, 0, 0, 0)
    return jsonify(
        {
            "items": cart,
            "subtotal": subtotal,
            "gst": gst,
            "labour_charge": labour,
            "transport_charge": transport,
            "discount_amount": discount,
            "total": total,
        }
    )


@api_bp.route("/customers", methods=["POST"])
@login_required
def customers_save():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Customer name is required"}), 400
    saved = save_customer(
        {
            "name": name,
            "phone": data.get("phone", "").strip(),
            "email": data.get("email", "").strip(),
            "address": data.get("address", "").strip(),
        }
    )
    return jsonify(saved)


@api_bp.route("/cart/clear", methods=["POST"])
@login_required
def cart_clear():
    session["cart"] = []
    session.modified = True
    return jsonify({"items": []})


@api_bp.route("/quotations", methods=["GET"])
@login_required
def quotations_list():
    return jsonify(list_quotations())


@api_bp.route("/quotations", methods=["POST"])
@login_required
def quotations_create():
    data = request.get_json() or {}
    cart = _cart()
    if len(cart) < 1:
        return jsonify({"error": "Cart is empty"}), 400

    min_items = int(data.get("min_items", 2))
    if len(cart) < min_items and data.get("action") in ("generate", "continue"):
        return jsonify(
            {"error": f"Please add at least {min_items} trees before generating a quotation"}
        ), 400

    customer_name = (data.get("customer") or {}).get("name", "").strip()
    if not customer_name:
        return jsonify({"error": "Customer name is required"}), 400

    charges = data.get("charges") or {}

    items = [
        {
            "name": i["name"],
            "scientific": i.get("scientific", ""),
            "particular": i.get("name", ""),
            "qty": i["qty"],
            "height": i.get("height", ""),
            "spacing": i.get("spacing", ""),
            "remarks": i.get("remarks", ""),
            "price": float(i.get("rate", i["price"])),
            "rate": float(i.get("rate", i["price"])),
            "total": round(float(i.get("rate", i["price"])) * i["qty"], 2),
        }
        for i in cart
    ]
    subtotal, gst, labour, transport, discount, total = _calc_totals(cart, charges)
    customer = data.get("customer") or {}

    payload = {
        "customer_name": customer_name,
        "customer_phone": customer.get("phone", ""),
        "customer_email": customer.get("email", ""),
        "customer_address": customer.get("address", ""),
        "items": items,
        "subtotal": subtotal,
        "gst_amount": gst,
        "labour_charge": labour,
        "transport_charge": transport,
        "discount_amount": discount,
        "total": total,
        "quote_note": data.get("quote_note", Config.QUOTE_NOTE),
        "status": data.get("status", "Draft"),
    }

    saved = save_quotation(payload)
    result = {"quotation_no": saved["quotation_no"], "total": total}

    if data.get("generate_pdf"):
        pdf_path = generate_quotation_pdf({**payload, "quotation_no": saved["quotation_no"]})
        set_quotation_pdf(saved["quotation_no"], pdf_path)
        if payload["status"] == "Draft":
            update_quotation_status(saved["quotation_no"], "Sent")
        result["pdf_url"] = f"/quotations/{saved['quotation_no']}/pdf"

    if data.get("clear_cart"):
        session["cart"] = []

    session.modified = True
    return jsonify(result)


@api_bp.route("/payment/create", methods=["POST"])
@login_required
def payment_create():
    data = request.get_json() or {}
    quotation_no = data.get("quotation_no")

    if quotation_no:
        q = get_quotation(quotation_no)
        if not q:
            return jsonify({"error": "Quotation not found"}), 404
        amount = q["total"]
    else:
        cart = _cart()
        if not cart:
            return jsonify({"error": "Nothing to pay for"}), 400
        customer = data.get("customer") or {}
        if not customer.get("name", "").strip():
            return jsonify({"error": "Customer name required"}), 400
        items = [
            {
                "name": i["name"],
                "qty": i["qty"],
                "height": i.get("height", ""),
                "spacing": i.get("spacing", ""),
                "remarks": i.get("remarks", ""),
                "price": float(i.get("rate", i["price"])),
                "rate": float(i.get("rate", i["price"])),
                "total": round(float(i.get("rate", i["price"])) * i["qty"], 2),
            }
            for i in cart
        ]
        charges = data.get("charges") or {}
        subtotal, gst, labour, transport, discount, total = _calc_totals(cart, charges)
        saved = save_quotation(
            {
                "customer_name": customer["name"],
                "customer_phone": customer.get("phone", ""),
                "customer_email": customer.get("email", ""),
                "customer_address": customer.get("address", ""),
                "items": items,
                "subtotal": subtotal,
                "gst_amount": gst,
                "labour_charge": labour,
                "transport_charge": transport,
                "discount_amount": discount,
                "total": total,
                "quote_note": data.get("quote_note", Config.QUOTE_NOTE),
                "status": "Draft",
            }
        )
        quotation_no = saved["quotation_no"]
        amount = total

    order = create_payment_order(amount, quotation_no)
    return jsonify(order)


@api_bp.route("/payment/verify", methods=["POST"])
@login_required
def payment_verify():
    data = request.get_json() or {}
    quotation_no = data.get("quotation_no")
    order_id = data.get("razorpay_order_id") or data.get("order_id")
    payment_id = data.get("razorpay_payment_id") or data.get("payment_id")
    signature = data.get("razorpay_signature") or data.get("signature", "")

    if data.get("demo"):
        payment_id = payment_id or f"pay_demo_{quotation_no}"
        update_quotation_status(quotation_no, "Paid", payment_id)
        return jsonify({"success": True, "message": "Demo payment recorded"})

    if not verify_payment_signature(order_id, payment_id, signature):
        return jsonify({"error": "Invalid payment signature"}), 400

    update_quotation_status(quotation_no, "Paid", payment_id)
    return jsonify({"success": True})


@api_bp.route("/quotations/<quotation_no>", methods=["DELETE"])
@login_required
def quotation_delete(quotation_no):
    from app.models import db

    with db() as conn:
        conn.execute("DELETE FROM quotations WHERE quotation_no = ?", (quotation_no,))
    return jsonify({"ok": True})
