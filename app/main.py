import jwt
import time
from fastapi import FastAPI, HTTPException, Depends, Request
from .models.extractor_models import InvoiceRequest, InvoiceResponse, ExtractionRequest, ExtractionResponse
from .models.recipe_models import RecipeRequest, RecipeResponse, UserSubscription
from .agents.extractor import ExtractorAgent
from .agents.recipe_extractor import RecipeExtractorAgent
from .services.alby_client import AlbyClient, WEBHOOK_SECRET
from pydantic import BaseModel # <<< ADD THIS LINE
from .database import get_db, connect_to_db, close_db  # Import new functions
import aiosqlite
from svix.webhooks import Webhook


app = FastAPI(title="Agentic MVP")

# NEW: Use the correct lifespan events to manage our singleton connection
@app.on_event("startup")
async def startup_event():
    await connect_to_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

# Dependency Injection for our clients
def get_alby_client():
    return AlbyClient()

def get_extractor_agent():
    return ExtractorAgent()

def get_recipe_extractor():
    return RecipeExtractorAgent()

# NEW MODEL for webhook payload
class WebhookPayload(BaseModel):
    payment_hash: str



@app.post("/v1/invoice", response_model=InvoiceResponse)
async def create_payment_invoice(
    request: InvoiceRequest,
    db: aiosqlite.Connection = Depends(get_db),
    alby: AlbyClient = Depends(get_alby_client)
):
    try:
        invoice_data = alby.create_invoice(
            amount_sats=100, description="Payment for 1x Extractor Agent run"
        )
        # Immediately record the new invoice in our database as 'pending'
        await db.execute(
            "INSERT INTO invoices (payment_hash, status) VALUES (?, ?)",
            (invoice_data["payment_hash"], "pending")
        )
        await db.commit()
        return InvoiceResponse(
            payment_hash=invoice_data["payment_hash"],
            payment_request=invoice_data["payment_request"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {e}")

# NEW ENDPOINT: The webhook listener
@app.post("/v1/payment-callback")
async def payment_callback(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Listens for and verifies 'invoice.settled' webhooks from Alby via Svix."""
    try:
        # Get the headers Svix sends
        headers = request.headers
        # Get the raw request body
        payload = await request.body()
        
        # Initialize the Svix webhook verifier with our secret
        wh = Webhook(WEBHOOK_SECRET)
        
        # Verify the payload. This will raise an exception on failure.
        data = wh.verify(payload, headers)

        # If verification succeeds, the data is a dictionary of the payload.
        # Check the event type and extract the payment_hash.
        if data.get("state") == "SETTLED":
            payment_hash = data.get("payment_hash")
            if not payment_hash:
                raise HTTPException(status_code=400, detail="Missing payment_hash in payload")
            
            # Update our database
            await db.execute(
                "UPDATE invoices SET status = 'settled' WHERE payment_hash = ?",
                (payment_hash,)
            )
            await db.commit()
            print(f"--- Svix Webhook Verified: Invoice {payment_hash} settled! ---")
            return {"status": "ok"}
        else:
            # We received a valid webhook for an event we don't care about.
            print(f"Received unhandled Svix event state: {data.get('state')}")
            return {"status": "ok - unhandled event"}

    except Exception as e:
        # This will catch Svix verification errors and other issues.
        print(f"Webhook processing error: {e}")
        raise HTTPException(status_code=400, detail="Webhook verification failed.")


# NEW ENDPOINT: The client polling endpoint
@app.get("/v1/invoice/status/{payment_hash}")
async def get_invoice_status(
    payment_hash: str,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Allows the client to poll for the status of their payment."""
    cursor = await db.execute("SELECT status FROM invoices WHERE payment_hash = ?", (payment_hash,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"status": row[0]}


@app.post("/v1/extract", response_model=ExtractionResponse)
async def extract_content(
    request: ExtractionRequest,
    db: aiosqlite.Connection = Depends(get_db),
    agent: ExtractorAgent = Depends(get_extractor_agent)
):
    """Execute the agent. Now checks our internal DB instead of Alby's API."""
    payment_hash = request.payment_hash
    url = str(request.url)

    try:
        cursor = await db.execute("SELECT status FROM invoices WHERE payment_hash = ?", (payment_hash,))
        row = await cursor.fetchone()

        if not row or row[0] != 'settled':
            raise HTTPException(status_code=402, detail="Payment required or not yet settled.")

        # If we get here, payment is verified internally.
        result = agent.run(url=url)
        # On success
        await log_request(db, "/v1/extract", 200, payment_hash=payment_hash, url=url)
        return result

    except HTTPException as e:
        # Log known errors (402, 403)
        await log_request(db, "/v1/extract", e.status_code, payment_hash=payment_hash, url=url, error=e.detail)
        raise e

    except Exception as e:
        await log_request(db, "/v1/extract", 500, payment_hash=payment_hash, url=url, error=str(e))
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

async def log_request(db: aiosqlite.Connection, endpoint: str, status_code: int, payment_hash: str = None, url: str = None, error: str = None):
    await db.execute(
        "INSERT INTO api_logs (endpoint, status_code, payment_hash, url_requested, error_message) VALUES (?, ?, ?, ?, ?)",
        (endpoint, status_code, payment_hash, url, error)
    )
    await db.commit()

@app.post("/v1/extract-recipe", response_model=RecipeResponse)
async def extract_recipe(
    request: RecipeRequest,
    db: aiosqlite.Connection = Depends(get_db),
    recipe_extractor: RecipeExtractorAgent = Depends(get_recipe_extractor)
):
    """Extract recipe from a URL - supports free tier and subscriptions"""
    url = str(request.url)
    user_token = request.user_token
    
    try:
        # Check user subscription/credits
        if user_token:
            # Verify JWT token and get user info
            # For MVP, simplified auth - would need proper JWT validation
            cursor = await db.execute(
                "SELECT recipes_remaining, subscription_type FROM users WHERE token = ?",
                (user_token,)
            )
            user_data = await cursor.fetchone()
            
            if not user_data:
                # New user - give them free tier
                await db.execute(
                    "INSERT INTO users (token, recipes_remaining, subscription_type) VALUES (?, ?, ?)",
                    (user_token, 3, 'free')
                )
                await db.commit()
                recipes_remaining = 3
                subscription_type = 'free'
            else:
                recipes_remaining, subscription_type = user_data
            
            # Check if they have access
            if subscription_type == 'free' and recipes_remaining <= 0:
                raise HTTPException(status_code=402, detail="Free recipes exhausted. Please subscribe.")
            elif subscription_type == 'monthly':
                # Unlimited for monthly subscribers
                pass
            
            # Deduct credit for free tier
            if subscription_type == 'free':
                await db.execute(
                    "UPDATE users SET recipes_remaining = recipes_remaining - 1 WHERE token = ?",
                    (user_token,)
                )
                await db.commit()
        else:
            # No token - use anonymous free tier (3 per IP per month)
            # For MVP, simplified - would need proper IP tracking
            pass
        
        # Extract the recipe
        result = recipe_extractor.run(url=url, prefer_fast=True)
        
        # Log successful extraction
        await db.execute(
            "INSERT INTO recipe_extractions (url, user_token, extraction_method, confidence_score, cost_cents) VALUES (?, ?, ?, ?, ?)",
            (url, user_token, result.extraction_method, result.confidence_score, result.cost_cents)
        )
        await db.commit()
        
        return result
        
    except HTTPException as e:
        raise e
    except Exception as e:
        await log_request(db, "/v1/extract-recipe", 500, url=url, error=str(e))
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")