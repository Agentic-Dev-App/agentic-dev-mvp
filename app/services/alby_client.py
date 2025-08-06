import os
import requests
from dotenv import load_dotenv

load_dotenv()

ALBY_API_URL = "https://api.getalby.com"
ACCESS_TOKEN = os.getenv("ALBY_ACCESS_TOKEN")
# NEW: Load the webhook secret
WEBHOOK_SECRET = os.getenv("ALBY_WEBHOOK_SECRET") 
# The public URL for our callback endpoint
WEBHOOK_ENDPOINT = "https://api.agenticdev.app/v1/payment-callback"

if not ACCESS_TOKEN or not WEBHOOK_SECRET:
    raise ValueError("CRITICAL: ALBY_ACCESS_TOKEN or ALBY_WEBHOOK_SECRET not found in environment.")

class AlbyClient:
    def __init__(self):
        # THE FIX: We get the token from the environment HERE, inside the init method.
        # This ensures we get the most current value every time a client is created.
        access_token = os.getenv("ALBY_ACCESS_TOKEN")

        # The sanity check is now also inside the init method.
        if not access_token:
            raise ValueError("CRITICAL: AlbyClient initialized but ALBY_ACCESS_TOKEN was not found.")

        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def create_invoice(self, amount_sats: int, description: str) -> dict:
        payload = {
            "amount": amount_sats,
            "description": description,
            "webhook_endpoint": WEBHOOK_ENDPOINT # THE KEY ADDITION
        }
        response = requests.post(f"{ALBY_API_URL}/invoices", headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    # The is_invoice_paid method is now DEPRECATED and no longer used.
    # We will rely on our internal database, updated by the webhook.

    def is_invoice_paid(self, payment_hash: str) -> bool:
        """Checks if a specific invoice has been paid."""
        response = requests.get(f"{ALBY_API_URL}/invoices/{payment_hash}", headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return data.get("settled", False)