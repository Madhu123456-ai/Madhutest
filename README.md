# GreenFormula

Python web app for garden nursery quotation building, PDF generation, and payment (Razorpay or demo mode).

## Quick start

```bash
cd /var/www/greenformula
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: edit company & Razorpay keys
python run.py
```

Open **http://localhost:5050** (or set `PORT=5000`) and sign in:

- **Username:** `admin`
- **Password:** `admin123`

## Features

- Admin login (single user)
- Tree directory search with name, scientific name, and price
- Cart with GST (18%) and minimum 2 trees before “Continue”
- PDF quotation with company logo, address, GSTIN, and customer details
- Razorpay payments when `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` are set; otherwise demo payment flow
- Recent quotations table with download and delete

## Configuration

Edit `.env` (see `.env.example`) for company details, admin password, and Razorpay keys.
