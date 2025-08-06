# app/database.py
import aiosqlite

DB_PATH = "/data/agentic_ledger.db"
_db = None

async def get_db():
    global _db
    if _db is None: raise RuntimeError("Database not initialized.")
    return _db

async def connect_to_db():
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    await _db.execute("PRAGMA journal_mode=WAL;") # Better concurrency
    
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            payment_hash TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending', -- pending, settled, expired
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Initialize the used_invoices table
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS used_invoices (
            payment_hash TEXT PRIMARY KEY,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Add recipe-specific tables
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            token TEXT PRIMARY KEY,
            email TEXT,
            recipes_remaining INTEGER DEFAULT 3,
            subscription_type TEXT DEFAULT 'free', -- free, monthly, payperuse
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS recipe_extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            user_token TEXT,
            extraction_method TEXT,
            confidence_score REAL,
            cost_cents REAL,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT,
            status_code INTEGER,
            payment_hash TEXT,
            url_requested TEXT,
            error_message TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await _db.commit()
    print("--- Database connection established and tables initialized ---")

async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
        print("--- Database connection closed ---")