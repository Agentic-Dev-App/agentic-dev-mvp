from pydantic import BaseModel, HttpUrl
from typing import Optional

# NEW: Models for Invoicing
class InvoiceRequest(BaseModel):
    # In the future, we could specify agent_name, etc.
    pass

class InvoiceResponse(BaseModel):
    payment_hash: str
    payment_request: str # This is the BOLT11 invoice string

# MODIFIED: Request for the agent now requires proof of payment
class ExtractionRequest(BaseModel):
    url: HttpUrl
    payment_hash: str

class ExtractionResponse(BaseModel):
    status: str
    url: Optional[HttpUrl] = None
    title: Optional[str] = None
    text_content: Optional[str] = None
    error: Optional[str] = None