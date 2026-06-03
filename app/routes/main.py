from flask import Blueprint, redirect, render_template, send_file, url_for
from flask_login import login_required

from app.config import Config
from app.models import get_featured_trees, get_quotation, get_stats, list_quotations

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        company={
            "name": Config.COMPANY_NAME,
            "address": Config.COMPANY_ADDRESS,
            "phone": Config.COMPANY_PHONE,
            "email": Config.COMPANY_EMAIL,
            "gstin": Config.COMPANY_GSTIN,
            "gst_rate": Config.GST_RATE,
            "quote_note": Config.QUOTE_NOTE,
        },
        stats=get_stats(),
        featured=get_featured_trees(),
        quotations=list_quotations(),
        razorpay_enabled=Config().razorpay_enabled,
        razorpay_key=Config.RAZORPAY_KEY_ID or "",
    )


@main_bp.route("/quotations/<quotation_no>/pdf")
@login_required
def download_pdf(quotation_no):
    q = get_quotation(quotation_no)
    if not q or not q.get("pdf_path"):
        return "PDF not found", 404
    return send_file(q["pdf_path"], as_attachment=True, download_name=f"{quotation_no}.pdf")
