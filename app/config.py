import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv("SECRET_KEY", "greenformula-dev-secret-change-me")
    DATABASE = str(BASE_DIR / "data" / "greenformula.db")
    UPLOAD_DIR = BASE_DIR / "static" / "uploads"
    PDF_DIR = BASE_DIR / "data" / "quotations"

    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

    COMPANY_NAME = os.getenv("COMPANY_NAME", "GreenFormula Landscape and Gardening Solution")
    COMPANY_ADDRESS = os.getenv(
        "COMPANY_ADDRESS",
        "233/2, Sriperumbudur Main Road, Chennai, TAMIL NADU 601301",
    )
    COMPANY_PHONE = os.getenv("COMPANY_PHONE", "+918015355447")
    COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "selva@greenformula.com")
    COMPANY_GSTIN = os.getenv("COMPANY_GSTIN", "29ABCDE1234F1Z5")
    GST_RATE = float(os.getenv("GST_RATE", "18"))
    QUOTE_NOTE = os.getenv(
        "QUOTE_NOTE",
        "We Team Green formula Landscapers...Happy Graderning",
    )

    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

    @property
    def razorpay_enabled(self):
        return bool(self.RAZORPAY_KEY_ID and self.RAZORPAY_KEY_SECRET)
