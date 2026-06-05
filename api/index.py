"""Luhn Generator Web API - FastAPI backend."""
import sys
import os

# Add the luhn-generator scripts to path
sys.path.insert(0, os.path.expanduser("~/.hermes/skills/luhn-generator/scripts"))

from fastapi import FastAPI, Query
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
    parse_card, BIN_DATABASE, BANK_BINS, cards_to_pipe,
    get_tracker_stats, get_bin_recommendations, track_check
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

class TrackRequest(BaseModel):
    card: str
    status: str  # live, die, unknown

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
    result = lookup_bin_online(bin_number, use_cache=True)
    return result

@app.post("/api/validate")
def api_validate(number: str):
    """Validate a card number."""
    return validate_card(number)

@app.post("/api/parse")
def api_parse(card: str):
    """Parse a card number: extract BIN, bank, country."""
    return parse_card(card)

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

@app.get("/api/stats")
def api_stats():
    """Get tracker statistics."""
    return get_tracker_stats()

@app.get("/api/recommend")
def api_recommend():
    """Get BIN recommendations."""
    return {"recommendations": get_bin_recommendations(10)}

@app.post("/api/track")
def api_track(req: TrackRequest):
    """Record a check result."""
    clean = req.card.split("|")[0] if "|" in req.card else req.card
    bin_prefix = clean[:6]
    bin_info = lookup_bin(bin_prefix)
    track_check(
        card_number=clean, status=req.status.lower(),
        bin_number=bin_prefix,
        bank=bin_info.get("bank"), country=bin_info.get("country"),
        network=_detect_network(clean)
    )
    return {"status": "recorded", "card": clean[-4:], "result": req.status}

# ─── Serve Frontend ───────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    try:
        from api._html import INDEX_HTML
        return HTMLResponse(INDEX_HTML)
    except ImportError:
        from _html import INDEX_HTML
        return HTMLResponse(INDEX_HTML)
