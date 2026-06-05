"""Luhn Generator Web API - FastAPI backend (Vercel-ready)."""
import sys
import os

# Fix import path: luhn_generator.py is in same directory as this file
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json

# Import the luhn generator
from luhn_generator import (
    generate_batch, generate_card, enrich_card, enrich_cards_batch,
    format_card, FORMATTERS, lookup_bin_online, lookup_bin,
    batch_lookup_bins, _detect_network, generate_name, generate_address,
    generate_phone, _resolve_country, is_valid_luhn, validate_card,
    parse_card, BIN_DATABASE, BANK_BINS, cards_to_pipe
)

app = FastAPI(title="Luhn Generator Web", version="3.4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ───────────────────────────────────

class GenerateRequest(BaseModel):
    count: int = 10
    bins: Optional[List[str]] = None
    types: Optional[List[str]] = None

class EnrichRequest(BaseModel):
    cards: List[str]

class FormatRequest(BaseModel):
    cards: List[str]
    site: str = "stripe"

class LookupRequest(BaseModel):
    bins: List[str]

# ─── API Routes ───────────────────────────────

@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    """Generate cards with optional BIN and type filters."""
    cards = generate_batch(
        count=req.count,
        card_types=req.types,
        custom_bins=req.bins
    )
    # Enrich each card with profile data
    enriched = []
    for c in cards:
        bin_prefix = c.get("bin", "")[:6]
        bin_info = lookup_bin(bin_prefix)
        country = bin_info.get("country", "US")
        cc = _resolve_country(country)
        c["phone"] = generate_phone(cc)
        enriched.append(c)
    
    # Pipe format for copy
    pipes = []
    for c in enriched:
        raw = c["raw_number"]
        m, y = c["expiry"].split("/")
        pipes.append(f"{raw}|{m}|{y}|{c['cvv']}")
    
    return {
        "cards": enriched,
        "pipe": "\n".join(pipes),
        "count": len(enriched)
    }

@app.post("/api/enrich")
def api_enrich(req: EnrichRequest):
    """Enrich existing cards with name, address, phone, BIN info."""
    enriched = enrich_cards_batch(req.cards)
    pipes = []
    for e in enriched:
        if "error" not in e:
            raw = e.get("raw_number", "")
            exp = e.get("expiry", "12/2028")
            m, y = exp.split("/")
            cvv = e.get("cvv", "000")
            pipes.append(f"{raw}|{m}|{y}|{cvv}")
    return {
        "cards": enriched,
        "pipe": "\n".join(pipes),
        "count": len(enriched)
    }

@app.post("/api/format")
def api_format(req: FormatRequest):
    """Format cards for specific checkout sites."""
    enriched = enrich_cards_batch(req.cards)
    formatted = []
    for e in enriched:
        if "error" not in e:
            formatted.append(format_card(e, req.site))
    return {
        "formatted": formatted,
        "site": req.site,
        "count": len(formatted)
    }

@app.post("/api/lookup")
def api_lookup(req: LookupRequest):
    """Look up BIN information."""
    results = batch_lookup_bins(req.bins)
    return {"results": results}

@app.get("/api/lookup/{bin_number}")
def api_lookup_single(bin_number: str):
    """Look up a single BIN."""
    result = lookup_bin_online(bin_number, use_cache=False)
    return result

@app.post("/api/validate")
def api_validate_card(number: str):
    """Validate a card number."""
    return validate_card(number)

@app.get("/api/bins")
def api_list_bins():
    """List all BINs in database."""
    bins = []
    for bin_num, info in sorted(BANK_BINS.items()):
        bins.append({
            "bin": bin_num,
            "bank": info["bank"],
            "type": info["type"],
            "country": info["country"]
        })
    return {"bins": bins, "count": len(bins)}

@app.get("/api/types")
def api_list_types():
    """List supported card types."""
    types = []
    for name, info in BIN_DATABASE.items():
        types.append({
            "id": name,
            "name": info["name"],
            "prefixes": info["prefixes"],
            "lengths": info["lengths"]
        })
    return {"types": types}

# ─── Serve Frontend ───────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    try:
        from _html import INDEX_HTML
        return HTMLResponse(INDEX_HTML)
    except ImportError:
        return HTMLResponse("<h1>Luhn Generator v3.4</h1><p>Frontend loading error. Check api/_html.py</p>")
