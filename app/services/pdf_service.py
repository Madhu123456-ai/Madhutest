from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from app.config import Config


class QuotationPDF(FPDF):
    def header(self):
        self.set_fill_color(26, 92, 46)
        self.rect(0, 0, 210, 45, "F")
        logo_path = Config.BASE_DIR / "static" / "images" / "logo.jpg"
        if logo_path.exists():
            self.image(str(logo_path), x=10, y=8, w=25)
        self.set_text_color(255, 255, 255)
        self.set_xy(40, 7)
        self.set_font("Arial", "B", 14)
        self.cell(0, 7, Config.COMPANY_NAME, ln=1)
        self.set_x(40)
        self.set_font("Arial", "", 9)
        self.multi_cell(0, 5, Config.COMPANY_ADDRESS)
        self.set_x(40)
        self.cell(0, 5, "Phone: {} | Email: {}".format(Config.COMPANY_PHONE, Config.COMPANY_EMAIL), ln=1)
        self.set_x(40)
        self.cell(0, 5, "GSTIN: {}".format(Config.COMPANY_GSTIN), ln=1)
        self.set_y(50)
        self.set_text_color(0, 0, 0)


def generate_quotation_pdf(quotation):
    """Generate PDF and return file path."""
    Config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    filename = "{}.pdf".format(quotation["quotation_no"])
    filepath = Config.PDF_DIR / filename

    pdf = QuotationPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(26, 92, 46)
    pdf.cell(0, 10, "QUOTATION - {}".format(quotation["quotation_no"]), ln=1)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Date: {}".format(datetime.utcnow().strftime("%d %b %Y")), ln=1)
    pdf.ln(4)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "Bill To:", ln=1)
    pdf.set_font("Arial", "", 10)
    for line in [
        quotation.get("customer_name", ""),
        quotation.get("customer_phone", ""),
        quotation.get("customer_email", ""),
        quotation.get("customer_address", ""),
    ]:
        if line:
            pdf.multi_cell(0, 5, line)
    pdf.ln(4)

    pdf.set_fill_color(26, 92, 46)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 8)
    col_w = [10, 42, 18, 20, 20, 24, 24, 32]
    headers = ["S.No", "Particular", "Qty", "Height", "Rate", "Amount", "Spacing", "Remarks"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 8)
    for idx, item in enumerate(quotation["items"], 1):
        total = item.get("total") or item.get("rate", item.get("price", 0)) * item.get("qty", 1)
        row = [
            str(idx),
            item.get("particular", item.get("name", ""))[:22],
            str(item.get("qty", 1)),
            str(item.get("height", ""))[:10],
            "Rs {:.2f}".format(item.get("rate", item.get("price", 0))),
            "Rs {:.2f}".format(total),
            str(item.get("spacing", ""))[:12],
            str(item.get("remarks", ""))[:20],
        ]
        for i, val in enumerate(row):
            pdf.cell(col_w[i], 7, val, border=1, align="R" if i > 1 else "L")
        pdf.ln()

    pdf.ln(4)
    pdf.set_font("Arial", "", 10)
    summary = [
        ("Subtotal:", quotation["subtotal"]),
        ("GST ({}%):".format(Config.GST_RATE), quotation["gst_amount"]),
        ("Labour Charge:", quotation.get("labour_charge", 0)),
        ("Transport Charge:", quotation.get("transport_charge", 0)),
        ("Discount:", quotation.get("discount_amount", 0)),
        ("Total:", quotation["total"]),
    ]
    for label, amount in summary:
        pdf.cell(130, 7, label, align="R")
        pdf.set_font("Arial", "B" if label.startswith("Total") else "", 10)
        pdf.cell(50, 7, "Rs {:.2f}".format(amount), ln=1, align="R")
        pdf.set_font("Arial", "", 10)

    pdf.ln(8)
    pdf.set_font("Arial", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, quotation.get("quote_note", Config.QUOTE_NOTE), align="C")

    pdf.output(str(filepath))
    return str(filepath)
