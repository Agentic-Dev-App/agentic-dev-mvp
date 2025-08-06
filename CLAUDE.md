# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based payment-gated API service that provides web content extraction capabilities. The service requires Lightning Network micropayments (via Alby) before allowing access to the extraction agent.

## Core Architecture

### Payment Flow
1. Client requests invoice via `/v1/invoice` endpoint
2. Invoice creation through Alby API returns payment_hash and BOLT11 payment_request
3. Client pays invoice through Lightning Network
4. Alby sends webhook to `/v1/payment-callback` when invoice is settled
5. Webhook updates local SQLite database invoice status
6. Client polls `/v1/invoice/status/{payment_hash}` or proceeds to use extraction service
7. `/v1/extract` endpoint verifies payment status from local database before processing

### Key Components

- **app/main.py**: FastAPI application with payment verification and webhook handling
- **app/database.py**: SQLite database management with singleton connection pattern, stores invoice states
- **app/services/alby_client.py**: Alby Lightning Network payment integration
- **app/agents/extractor.py**: Web content extraction using trafilatura library
- **app/models/extractor_models.py**: Pydantic models for request/response validation

### Database Schema

Two tables managed in SQLite (`/data/agentic_ledger.db`):
- `invoices`: Tracks payment_hash, status (pending/settled/expired), created_at
- `used_invoices`: Prevents invoice reuse (payment_hash, used_at)

## Development Commands

### Running the Application

Local development:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docker deployment:
```bash
docker build -t agentic-mvp .
docker run -p 80:80 agentic-mvp
```

### Environment Variables

Required in `.env` file:
- `ALBY_ACCESS_TOKEN`: Bearer token for Alby API authentication
- `ALBY_WEBHOOK_SECRET`: Svix webhook secret for payment callback verification

## API Endpoints

- `POST /v1/invoice`: Create Lightning invoice (100 sats)
- `POST /v1/payment-callback`: Webhook endpoint for Alby payment notifications (uses Svix verification)
- `GET /v1/invoice/status/{payment_hash}`: Check payment status
- `POST /v1/extract`: Execute content extraction (requires settled payment_hash)

## Dependencies

Key libraries:
- FastAPI/Uvicorn for API framework
- trafilatura for web content extraction
- aiosqlite for async database operations
- svix for webhook signature verification
- PyJWT for token handling
- python-dotenv for environment configuration