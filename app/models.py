import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.config import Config


def get_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    from pathlib import Path

    Config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    Path(Config.DATABASE).parent.mkdir(parents=True, exist_ok=True)

    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS admin_user (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scientific TEXT,
                price REAL NOT NULL,
                category TEXT,
                image_url TEXT
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_no TEXT UNIQUE NOT NULL,
                customer_id INTEGER,
                customer_name TEXT,
                customer_phone TEXT,
                customer_email TEXT,
                customer_address TEXT,
                items_json TEXT NOT NULL,
                subtotal REAL NOT NULL,
                gst_amount REAL NOT NULL,
                labour_charge REAL DEFAULT 0,
                transport_charge REAL DEFAULT 0,
                discount_amount REAL DEFAULT 0,
                total REAL NOT NULL,
                quote_note TEXT,
                status TEXT DEFAULT 'Draft',
                pdf_path TEXT,
                payment_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            """
        )

        def ensure_column(table_name, column_name, definition):
            columns = [
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            ]
            if column_name not in columns:
                conn.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
                )

        ensure_column("quotations", "labour_charge", "REAL DEFAULT 0")
        ensure_column("quotations", "transport_charge", "REAL DEFAULT 0")
        ensure_column("quotations", "discount_amount", "REAL DEFAULT 0")
        ensure_column("quotations", "quote_note", "TEXT")

        row = conn.execute(
            "SELECT id FROM admin_user WHERE username = ?", (Config.ADMIN_USERNAME,)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO admin_user (username, password_hash) VALUES (?, ?)",
                (
                    Config.ADMIN_USERNAME,
                    generate_password_hash(Config.ADMIN_PASSWORD),
                ),
            )

        count = conn.execute("SELECT COUNT(*) AS c FROM trees").fetchone()["c"]
        if count == 0:
            from app.data.trees_catalog import TREES

            for t in TREES:
                conn.execute(
                    """
                    INSERT INTO trees (name, scientific, price, category)
                    VALUES (?, ?, ?, ?)
                    """,
                    (t["name"], t["scientific"], t["price"], t["category"]),
                )


def verify_admin(username: str, password: str) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT password_hash FROM admin_user WHERE username = ?", (username,)
        ).fetchone()
    if not row:
        return False
    return check_password_hash(row["password_hash"], password)


def search_trees(query: str, limit: int = 10):
    q = f"%{query.strip()}%"
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, name, scientific, price, category
            FROM trees
            WHERE name LIKE ? OR scientific LIKE ? OR category LIKE ?
            ORDER BY name
            LIMIT ?
            """,
            (q, q, q, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_tree(tree_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM trees WHERE id = ?", (tree_id,)).fetchone()
    return dict(row) if row else None


def get_featured_trees(limit: int = 4):
    names = ["Neem Tree", "Coconut Tree", "Guava Tree", "Lemon Tree"]
    with db() as conn:
        placeholders = ",".join("?" * len(names))
        rows = conn.execute(
            f"""
            SELECT id, name, scientific, price, category
            FROM trees WHERE name IN ({placeholders})
            """,
            names,
        ).fetchall()
    result = [dict(r) for r in rows]
    if len(result) < limit:
        with db() as conn:
            extra = conn.execute(
                "SELECT id, name, scientific, price, category FROM trees LIMIT ?",
                (limit - len(result),),
            ).fetchall()
        seen = {t["id"] for t in result}
        for r in extra:
            d = dict(r)
            if d["id"] not in seen:
                result.append(d)
    return result[:limit]


def next_quotation_no():
    with db() as conn:
        row = conn.execute(
            "SELECT quotation_no FROM quotations ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return "QTN-1001"
    num = int(row["quotation_no"].split("-")[-1]) + 1
    return f"QTN-{num}"


def save_quotation(data: dict) -> dict:
    qno = next_quotation_no()
    now = datetime.utcnow().isoformat(timespec="seconds")
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO quotations (
                quotation_no, customer_name, customer_phone, customer_email,
                customer_address, items_json, subtotal, gst_amount, labour_charge,
                transport_charge, discount_amount, total, quote_note, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                qno,
                data["customer_name"],
                data.get("customer_phone", ""),
                data.get("customer_email", ""),
                data.get("customer_address", ""),
                json.dumps(data["items"]),
                data["subtotal"],
                data["gst_amount"],
                data.get("labour_charge", 0),
                data.get("transport_charge", 0),
                data.get("discount_amount", 0),
                data["total"],
                data.get("quote_note", ""),
                data.get("status", "Draft"),
                now,
            ),
        )
        qid = cur.lastrowid
    return {"id": qid, "quotation_no": qno, **data}


def save_customer(data: dict) -> dict:
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO customers (name, phone, email, address)
            VALUES (?, ?, ?, ?)
            """,
            (
                data.get("name", ""),
                data.get("phone", ""),
                data.get("email", ""),
                data.get("address", ""),
            ),
        )
        customer_id = cur.lastrowid
    return {"id": customer_id, **data}


def update_quotation_status(quotation_no: str, status: str, payment_id: str = None):
    with db() as conn:
        if payment_id:
            conn.execute(
                "UPDATE quotations SET status = ?, payment_id = ? WHERE quotation_no = ?",
                (status, payment_id, quotation_no),
            )
        else:
            conn.execute(
                "UPDATE quotations SET status = ? WHERE quotation_no = ?",
                (status, quotation_no),
            )


def set_quotation_pdf(quotation_no: str, pdf_path: str):
    with db() as conn:
        conn.execute(
            "UPDATE quotations SET pdf_path = ? WHERE quotation_no = ?",
            (pdf_path, quotation_no),
        )


def get_quotation(quotation_no: str):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM quotations WHERE quotation_no = ?", (quotation_no,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["items"] = json.loads(d["items_json"])
    return d


def list_quotations(limit: int = 20):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT quotation_no, customer_name, total, status, created_at, pdf_path
            FROM quotations ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats():
    with db() as conn:
        quotations = conn.execute("SELECT COUNT(*) AS c FROM quotations").fetchone()["c"]
        customers = conn.execute(
            "SELECT COUNT(DISTINCT customer_name) AS c FROM quotations WHERE customer_name != ''"
        ).fetchone()["c"]
        products = conn.execute("SELECT COUNT(*) AS c FROM trees").fetchone()["c"]
        sales = conn.execute(
            """
            SELECT COALESCE(SUM(total), 0) AS s FROM quotations
            WHERE status = 'Paid' AND created_at >= date('now', 'start of month')
            """
        ).fetchone()["s"]
    return {
        "total_sales": float(sales or 0),
        "total_quotations": quotations,
        "total_customers": customers,
        "total_products": products,
    }
