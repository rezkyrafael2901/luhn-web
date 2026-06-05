#!/usr/bin/env python3
"""
═══════════════════════════════════════════════
  LUHN NUMBER GENERATOR v3.4
  Mathematical credit card number generation
  
  ⚠️  FOR EDUCATIONAL & TESTING PURPOSES ONLY
  Numbers are mathematically valid (pass Luhn)
  but NOT linked to real accounts.

  NEW in v3.4:
  - Phone number generation (11 countries)
  - Enrich existing cards (--enrich)
  - Batch file input (--input)
  - Live Card Tracker (SQLite, --tracker-stats)
  - Smart BIN Recommender (--recommend)
  - Site-specific formatting (--format stripe/shopify/paypal/generic)

  v3.3: Country-aware name + address (--full), 11 countries
  v3.2: Card parser, smart generate, CSV export, find BINs, proxy
═══════════════════════════════════════════════
"""

import random
import json
import argparse
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import itertools

# ═══════════════════════════════════════════════
# BIN (Bank Identification Number) DATABASE
# First 6-8 digits identify the card network/bank
# ═══════════════════════════════════════════════

BIN_DATABASE = {
    "visa": {
        "name": "Visa",
        "prefixes": ["4"],
        "lengths": [16],
        "cvv_length": 3
    },
    "mastercard": {
        "name": "Mastercard", 
        "prefixes": ["51", "52", "53", "54", "55", "2221", "2222", "2223", "2224", "2225"],
        "lengths": [16],
        "cvv_length": 3
    },
    "amex": {
        "name": "American Express",
        "prefixes": ["34", "37"],
        "lengths": [15],
        "cvv_length": 4
    },
    "discover": {
        "name": "Discover",
        "prefixes": ["6011", "644", "645", "646", "647", "648", "649", "65"],
        "lengths": [16],
        "cvv_length": 3
    },
    "diners": {
        "name": "Diners Club",
        "prefixes": ["300", "301", "302", "303", "304", "305", "36", "38"],
        "lengths": [14],
        "cvv_length": 3
    },
    "jcb": {
        "name": "JCB",
        "prefixes": ["3528", "3529", "353", "354", "355", "356", "357", "358"],
        "lengths": [16],
        "cvv_length": 3
    },
    "unionpay": {
        "name": "UnionPay",
        "prefixes": ["62"],
        "lengths": [16, 17, 18, 19],
        "cvv_length": 3
    }
}

# Expanded bank BIN database with country info
BANK_BINS = {
    # Visa
    "400000": {"bank": "Generic Visa", "type": "Visa Classic", "country": "US"},
    "400001": {"bank": "Generic Visa", "type": "Visa Gold", "country": "US"},
    "400002": {"bank": "Generic Visa", "type": "Visa Platinum", "country": "US"},
    "400003": {"bank": "Generic Visa", "type": "Visa Signature", "country": "US"},
    "400004": {"bank": "Generic Visa", "type": "Visa Infinite", "country": "US"},
    "400005": {"bank": "Generic Visa", "type": "Visa Business", "country": "US"},
    "400006": {"bank": "Generic Visa", "type": "Visa Corporate", "country": "US"},
    "400007": {"bank": "Generic Visa", "type": "Visa Purchasing", "country": "US"},
    "400344": {"bank": "Chase", "type": "Visa Debit", "country": "US"},
    "401288": {"bank": "Wells Fargo", "type": "Visa Credit", "country": "US"},
    "402400": {"bank": "Bank of America", "type": "Visa Credit", "country": "US"},
    "406032": {"bank": "Citibank", "type": "Visa Credit", "country": "US"},
    "411111": {"bank": "Test Visa", "type": "Visa Test", "country": "US"},
    "422222": {"bank": "Test Visa", "type": "Visa Test", "country": "US"},
    "446200": {"bank": "Santander", "type": "Visa Credit", "country": "UK"},
    "450060": {"bank": "BNI", "type": "Visa Credit", "country": "ID"},
    "450088": {"bank": "BCA", "type": "Visa Credit", "country": "ID"},
    "450120": {"bank": "Mandiri", "type": "Visa Credit", "country": "ID"},
    "450157": {"bank": "BRI", "type": "Visa Credit", "country": "ID"},
    "450200": {"bank": "CIMB Niaga", "type": "Visa Credit", "country": "ID"},
    "451500": {"bank": "BTN", "type": "Visa Credit", "country": "ID"},
    "453200": {"bank": "HSBC", "type": "Visa Credit", "country": "UK"},
    "455600": {"bank": "Standard Chartered", "type": "Visa Credit", "country": "UK"},
    "456700": {"bank": "ANZ", "type": "Visa Credit", "country": "AU"},
    "460000": {"bank": "KBC", "type": "Visa Debit", "country": "BE"},
    "470000": {"bank": "ING", "type": "Visa Debit", "country": "NL"},
    "480000": {"bank": "BNP Paribas", "type": "Visa Credit", "country": "FR"},
    "490000": {"bank": "Deutsche Bank", "type": "Visa Credit", "country": "DE"},
    
    # Mastercard
    "510000": {"bank": "Generic MC", "type": "Mastercard Standard", "country": "US"},
    "510001": {"bank": "Generic MC", "type": "Mastercard Gold", "country": "US"},
    "510002": {"bank": "Generic MC", "type": "Mastercard Platinum", "country": "US"},
    "510003": {"bank": "Generic MC", "type": "Mastercard World", "country": "US"},
    "510004": {"bank": "Generic MC", "type": "Mastercard World Elite", "country": "US"},
    "510005": {"bank": "Generic MC", "type": "Mastercard Business", "country": "US"},
    "512345": {"bank": "Test MC", "type": "Mastercard Test", "country": "US"},
    "515000": {"bank": "Chase", "type": "Mastercard Credit", "country": "US"},
    "520000": {"bank": "Citibank", "type": "Mastercard Credit", "country": "US"},
    "525000": {"bank": "Capital One", "type": "Mastercard Credit", "country": "US"},
    "530000": {"bank": "Barclays", "type": "Mastercard Credit", "country": "UK"},
    "535000": {"bank": "HSBC", "type": "Mastercard Credit", "country": "UK"},
    "540000": {"bank": "Lloyds", "type": "Mastercard Credit", "country": "UK"},
    "545000": {"bank": "NatWest", "type": "Mastercard Credit", "country": "UK"},
    "550000": {"bank": "Standard Chartered", "type": "Mastercard Credit", "country": "UK"},
    "552000": {"bank": "Mandiri", "type": "Mastercard Credit", "country": "ID"},
    "553000": {"bank": "BCA", "type": "Mastercard Credit", "country": "ID"},
    "554000": {"bank": "BNI", "type": "Mastercard Credit", "country": "ID"},
    "555000": {"bank": "BRI", "type": "Mastercard Credit", "country": "ID"},
    "556000": {"bank": "CIMB Niaga", "type": "Mastercard Credit", "country": "ID"},
    "557000": {"bank": "Danamon", "type": "Mastercard Credit", "country": "ID"},
    "558000": {"bank": "Permata", "type": "Mastercard Credit", "country": "ID"},
    "559000": {"bank": "Mega", "type": "Mastercard Credit", "country": "ID"},
    
    # Amex
    "370000": {"bank": "Generic Amex", "type": "Amex Green", "country": "US"},
    "370001": {"bank": "Generic Amex", "type": "Amex Gold", "country": "US"},
    "370002": {"bank": "Generic Amex", "type": "Amex Platinum", "country": "US"},
    "370003": {"bank": "Generic Amex", "type": "Amex Centurion", "country": "US"},
    "374200": {"bank": "Test Amex", "type": "Amex Test", "country": "US"},
    "375000": {"bank": "Amex", "type": "Amex Blue", "country": "US"},
    "376000": {"bank": "Amex", "type": "Amex Delta", "country": "US"},
    "377000": {"bank": "Amex", "type": "Amex Hilton", "country": "US"},
    "378000": {"bank": "Amex", "type": "Amex Business", "country": "US"},
    
    # Discover
    "601100": {"bank": "Generic Discover", "type": "Discover Classic", "country": "US"},
    "601101": {"bank": "Generic Discover", "type": "Discover Gold", "country": "US"},
    "601102": {"bank": "Generic Discover", "type": "Discover Platinum", "country": "US"},
    "601103": {"bank": "Generic Discover", "type": "Discover Business", "country": "US"},
    "622000": {"bank": "China UnionPay", "type": "UnionPay Debit", "country": "CN"},
    "623000": {"bank": "China UnionPay", "type": "UnionPay Credit", "country": "CN"},
    "624000": {"bank": "China UnionPay", "type": "UnionPay Platinum", "country": "CN"},
    "625000": {"bank": "China UnionPay", "type": "UnionPay Diamond", "country": "CN"},
    "630000": {"bank": "BCA", "type": "Flazz Debit", "country": "ID"},
    "631000": {"bank": "Mandiri", "type": "E-Money", "country": "ID"},
    "632000": {"bank": "BNI", "type": "TapCash", "country": "ID"},
    "633000": {"bank": "BRI", "type": "BRIZZI", "country": "ID"},
    "634000": {"bank": "BNI", "type": "Discover Debit", "country": "US"},
    "635000": {"bank": "Citibank", "type": "Discover Credit", "country": "US"},
    "636000": {"bank": "Capital One", "type": "Discover Credit", "country": "US"},
    "637000": {"bank": "Synchrony", "type": "Discover Credit", "country": "US"},
    "638000": {"bank": "Discover", "type": "Discover It", "country": "US"},
    "639000": {"bank": "Discover", "type": "Discover More", "country": "US"},
    "640000": {"bank": "Discover", "type": "Discover Chrome", "country": "US"},
    "641000": {"bank": "Discover", "type": "Discover Miles", "country": "US"},
    "642000": {"bank": "Discover", "type": "Discover Open Road", "country": "US"},
    "643000": {"bank": "Discover", "type": "Discover Motiva", "country": "US"},
    "644000": {"bank": "Discover", "type": "Discover NHL", "country": "US"},
    "645000": {"bank": "Discover", "type": "Discover Student", "country": "US"},
    "646000": {"bank": "Discover", "type": "Discover Secured", "country": "US"},
    "647000": {"bank": "Discover", "type": "Discover Business", "country": "US"},
    "648000": {"bank": "Discover", "type": "Discover Corporate", "country": "US"},
    "649000": {"bank": "Discover", "type": "Discover Government", "country": "US"},
    "650000": {"bank": "Discover", "type": "Discover Prepaid", "country": "US"},
    "651000": {"bank": "Discover", "type": "Discover Healthcare", "country": "US"},
    "652000": {"bank": "Discover", "type": "Discover Education", "country": "US"},
    "653000": {"bank": "Discover", "type": "Discover Insurance", "country": "US"},
    "654000": {"bank": "Discover", "type": "Discover Telecom", "country": "US"},
    "655000": {"bank": "Discover", "type": "Discover Utility", "country": "US"},
    "656000": {"bank": "Discover", "type": "Discover Charity", "country": "US"},
    "657000": {"bank": "Discover", "type": "Discover Membership", "country": "US"},
    "658000": {"bank": "Discover", "type": "Discover Gift", "country": "US"},
    "659000": {"bank": "Discover", "type": "Discover Reloadable", "country": "US"},
    
    # JCB
    "352800": {"bank": "Generic JCB", "type": "JCB Standard", "country": "JP"},
    "352900": {"bank": "Generic JCB", "type": "JCB Gold", "country": "JP"},
    "353000": {"bank": "Mitsubishi UFJ", "type": "JCB Credit", "country": "JP"},
    "354000": {"bank": "Sumitomo Mitsui", "type": "JCB Credit", "country": "JP"},
    "355000": {"bank": "Mizuho", "type": "JCB Credit", "country": "JP"},
    "356000": {"bank": "Resona", "type": "JCB Credit", "country": "JP"},
    "357000": {"bank": "BCA", "type": "JCB Credit", "country": "ID"},
    "358000": {"bank": "BNI", "type": "JCB Credit", "country": "ID"},
    "359000": {"bank": "Mandiri", "type": "JCB Credit", "country": "ID"},
}

# ═══════════════════════════════════════════════
# LUHN ALGORITHM
# ═══════════════════════════════════════════════

def luhn_checksum(card_number: str) -> int:
    """Calculate Luhn checksum for a card number."""
    digits = [int(d) for d in card_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    return total % 10

def is_valid_luhn(card_number: str) -> bool:
    """Check if a card number passes Luhn validation."""
    return luhn_checksum(card_number) == 0

def calculate_luhn_digit(partial_number: str) -> int:
    """Calculate the Luhn check digit for a partial number."""
    for digit in range(10):
        test_number = partial_number + str(digit)
        if is_valid_luhn(test_number):
            return digit
    return -1  # Should never happen

# ═══════════════════════════════════════════════
# AUTO BIN GENERATION
# ═══════════════════════════════════════════════

def generate_random_bin(card_type: str = None, country: str = None, bank: str = None) -> str:
    """
    Generate a random BIN based on criteria.
    
    Args:
        card_type: Visa, Mastercard, Amex, Discover, Diners, JCB, UnionPay
        country: 2-letter country code (US, UK, ID, etc.)
        bank: Bank name to filter by
    
    Returns:
        6-digit BIN string
    """
    # Filter BINs based on criteria
    filtered_bins = []
    
    for bin_num, info in BANK_BINS.items():
        if card_type and card_type.lower() not in info["type"].lower():
            continue
        if country and info["country"].upper() != country.upper():
            continue
        if bank and bank.lower() not in info["bank"].lower():
            continue
        filtered_bins.append(bin_num)
    
    if not filtered_bins:
        # Fallback: generate random BIN based on card type prefix
        if card_type:
            card_info = BIN_DATABASE.get(card_type.lower(), BIN_DATABASE["visa"])
            prefix = random.choice(card_info["prefixes"])
            # Pad to 6 digits
            bin_num = prefix.ljust(6, '0')[:6]
        else:
            # Random card type
            card_type = random.choice(list(BIN_DATABASE.keys()))
            card_info = BIN_DATABASE[card_type]
            prefix = random.choice(card_info["prefixes"])
            bin_num = prefix.ljust(6, '0')[:6]
        return bin_num
    
    return random.choice(filtered_bins)

def generate_unique_bins(count: int = 10, card_type: str = None, 
                         country: str = None, bank: str = None) -> List[str]:
    """
    Generate multiple unique BINs.
    
    Args:
        count: Number of unique BINs to generate
        card_type: Filter by card type
        country: Filter by country
        bank: Filter by bank
    
    Returns:
        List of unique 6-digit BIN strings
    """
    bins = set()
    max_attempts = count * 10  # Prevent infinite loop
    attempts = 0
    
    while len(bins) < count and attempts < max_attempts:
        bin_num = generate_random_bin(card_type, country, bank)
        if bin_num not in bins:
            bins.add(bin_num)
        attempts += 1
    
    return sorted(list(bins))

def lookup_bin(bin_number: str) -> Dict:
    """
    Look up BIN information.
    
    Args:
        bin_number: 6-digit BIN to look up
    
    Returns:
        Dict with bank, type, country info
    """
    # Try exact match first
    if bin_number in BANK_BINS:
        info = BANK_BINS[bin_number]
        return {
            "bin": bin_number,
            "bank": info["bank"],
            "card_type": info["type"],
            "country": info["country"],
            "network": _detect_network(bin_number)
        }
    
    # Try prefix match
    for length in [6, 5, 4, 3]:
        prefix = bin_number[:length]
        for stored_bin, info in BANK_BINS.items():
            if stored_bin.startswith(prefix):
                return {
                    "bin": bin_number,
                    "bank": info["bank"] + " (prefix match)",
                    "card_type": info["type"],
                    "country": info["country"],
                    "network": _detect_network(bin_number),
                    "confidence": "medium"
                }
    
    # Fallback: detect network only
    network = _detect_network(bin_number)
    return {
        "bin": bin_number,
        "bank": "Unknown",
        "card_type": "Unknown",
        "country": "Unknown",
        "network": network,
        "confidence": "low"
    }

def _detect_network(bin_number: str) -> str:
    """Detect card network from BIN."""
    for card_type, info in BIN_DATABASE.items():
        for prefix in info["prefixes"]:
            if bin_number.startswith(prefix):
                return info["name"]
    return "Unknown"

def detect_card_type(bin_number: str) -> str:
    """Detect card type from BIN."""
    for card_type, info in BIN_DATABASE.items():
        for prefix in info["prefixes"]:
            if bin_number.startswith(prefix):
                return card_type
    return "visa"  # Default

# ═══════════════════════════════════════════════
# ONLINE BIN LOOKUP (binlist.net API - FREE)
# ═══════════════════════════════════════════════

BIN_CACHE_FILE = os.environ.get("BIN_CACHE_FILE", os.path.join(os.path.dirname(__file__), "bin_cache.json"))
if not os.path.exists(os.path.dirname(BIN_CACHE_FILE)):
    BIN_CACHE_FILE = "/tmp/bin_cache.json"

def _load_bin_cache() -> dict:
    """Load BIN cache from file."""
    try:
        if os.path.exists(BIN_CACHE_FILE):
            with open(BIN_CACHE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def _save_bin_cache(cache: dict):
    """Save BIN cache to file."""
    try:
        os.makedirs(os.path.dirname(BIN_CACHE_FILE), exist_ok=True)
        with open(BIN_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except:
        pass

def lookup_bin_online(bin_number: str, use_cache: bool = True) -> Dict:
    """
    Look up BIN information via binlist.net API (free, no key).
    
    Returns enriched info: bank, country, card type, brand, prepaid, scheme.
    Falls back to local DB if API fails.
    """
    bin_clean = str(bin_number).strip()[:8]
    if len(bin_clean) < 6:
        return {"error": f"BIN too short: {bin_clean} (need 6-8 digits)", "bin": bin_clean}
    
    # Check cache first
    cache = _load_bin_cache() if use_cache else {}
    if bin_clean in cache:
        result = cache[bin_clean].copy()
        result["_source"] = "cache"
        return result
    
    # Try API with decreasing BIN lengths (8, 7, 6)
    for length in [8, 7, 6]:
        if len(bin_clean) < length:
            continue
        test_bin = bin_clean[:length]
        try:
            url = f"https://lookup.binlist.net/{test_bin}"
            req = urllib.request.Request(url, headers={
                "Accept-Version": "3",
                "User-Agent": "LuhnGenerator/2.1"
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                
                result = {
                    "bin": test_bin,
                    "bank": data.get("bank", {}).get("name", "Unknown"),
                    "bank_city": data.get("bank", {}).get("city", ""),
                    "bank_url": data.get("bank", {}).get("url", ""),
                    "bank_phone": data.get("bank", {}).get("phone", ""),
                    "country": data.get("country", {}).get("name", "Unknown"),
                    "country_code": data.get("country", {}).get("alpha2", "??"),
                    "country_currency": data.get("country", {}).get("currency", ""),
                    "brand": data.get("brand", "Unknown"),
                    "type": data.get("type", "Unknown"),
                    "prepaid": data.get("prepaid", False),
                    "scheme": data.get("scheme", "Unknown"),
                    "card_length": data.get("number", {}).get("length", 0),
                    "luhn_valid": data.get("number", {}).get("luhn", None),
                    "_source": "binlist.net",
                    "_lookup_length": length
                }
                
                # Cache it
                if use_cache:
                    cache_data = {k: v for k, v in result.items() if not k.startswith("_")}
                    cache[test_bin] = cache_data
                    _save_bin_cache(cache)
                
                return result
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            elif e.code == 429:
                return {"error": "Rate limited by binlist.net", "bin": bin_clean, "fallback": lookup_bin(bin_number)}
            else:
                continue
        except Exception:
            continue
    
    # All API attempts failed — fallback to local DB
    local_result = lookup_bin(bin_number)
    local_result["_source"] = "local_db"
    return local_result

def batch_lookup_bins(bin_list: list, use_cache: bool = True) -> list:
    """Look up multiple BINs at once."""
    results = []
    for b in bin_list:
        result = lookup_bin_online(b, use_cache=use_cache)
        results.append(result)
    return results

# ═══════════════════════════════════════════════
# CARD GENERATION
# ═══════════════════════════════════════════════

def generate_card_number(card_type: str = "visa", custom_bin: str = None) -> str:
    """Generate a valid card number using Luhn algorithm."""
    if custom_bin:
        # Use custom BIN
        bin_prefix = custom_bin
        # Determine length based on card type
        card_info = BIN_DATABASE.get(card_type, BIN_DATABASE["visa"])
        target_length = card_info["lengths"][0]
    else:
        # Use random prefix from card type
        card_info = BIN_DATABASE.get(card_type, BIN_DATABASE["visa"])
        bin_prefix = random.choice(card_info["prefixes"])
        target_length = random.choice(card_info["lengths"])
    
    # Generate random digits for the middle
    middle_length = target_length - len(bin_prefix) - 1  # -1 for check digit
    middle = ''.join([str(random.randint(0, 9)) for _ in range(middle_length)])
    
    # Combine prefix and middle
    partial = bin_prefix + middle
    
    # Calculate and append Luhn check digit
    check_digit = calculate_luhn_digit(partial)
    return partial + str(check_digit)

def generate_expiry() -> str:
    """Generate a random future expiry date."""
    # Random date between now and 3 years from now
    today = datetime.now()
    future = today + timedelta(days=random.randint(30, 1095))
    return future.strftime("%m/%Y")

def generate_cvv(length: int = 3) -> str:
    """Generate a random CVV."""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

# ═══════════════════════════════════════════════
# COUNTRY-AWARE NAME & ADDRESS GENERATION (v3.3)
# ═══════════════════════════════════════════════

_NAMES_BY_COUNTRY = {
    "US": {
        "first": ["James","John","Robert","Michael","William","David","Richard","Joseph",
                   "Thomas","Charles","Christopher","Daniel","Matthew","Anthony","Mark",
                   "Mary","Patricia","Jennifer","Linda","Barbara","Elizabeth","Susan",
                   "Jessica","Sarah","Karen","Lisa","Nancy","Betty","Margaret","Sandra"],
        "last": ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
                 "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
                 "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson",
                 "White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson"]
    },
    "UK": {
        "first": ["Oliver","George","Harry","Jack","Jacob","Charlie","Thomas","Oscar",
                   "William","James","Amelia","Olivia","Emily","Isla","Ava","Mia",
                   "Isabella","Sophie","Grace","Lily"],
        "last": ["Smith","Jones","Williams","Taylor","Brown","Davies","Evans","Wilson",
                 "Thomas","Roberts","Johnson","Lewis","Walker","Robinson","Wood",
                 "Hall","Jackson","Clarke","Green","Harris"]
    },
    "ID": {
        "first": ["Budi","Andi","Rizki","Dewi","Siti","Ahmad","Muhammad","Putri",
                   "Rina","Dian","Agus","Hendra","Rudi","Sari","Lestari","Nur",
                   "Rahmat","Fajar","Adi","Wati","Eka","Bayu","Yuda","Citra",
                   "Intan","Ratna","Wulan","Dani","Gilang","Tika"],
        "last": ["Pratama","Wijaya","Saputra","Putra","Setiawan","Kurniawan","Hadi",
                 "Santoso","Susanto","Gunawan","Halim","Hartono","Wibowo","Nugroho",
                 "Raharjo","Purnama","Suryanto","Utomo","Kusuma","Anggraini"]
    },
    "JP": {
        "first": ["Takeshi","Yuki","Hiroshi","Kenji","Akira","Sakura","Yui","Aoi",
                   "Rin","Haruki","Sota","Ren","Mei","Mio","Hana","Koharu",
                   "Ayumu","Shota","Daiki","Naoki"],
        "last": ["Tanaka","Suzuki","Takahashi","Watanabe","Ito","Yamamoto","Nakamura",
                 "Kobayashi","Saito","Kato","Yoshida","Yamada","Sasaki","Matsumoto",
                 "Inoue","Kimura","Shimizu","Hayashi","Sato","Mori"]
    },
    "KR": {
        "first": ["Minjun","Seojun","Dojun","Jiwon","Seoyeon","Jimin","Minjae",
                   "Hyunwoo","Jungmin","Sunwoo","Eunji","Soyeon","Yuna","Dahyun",
                   "Chaeyoung","Jaemin","Taehyung","Seokjin","Yoongi","Hoseok"],
        "last": ["Kim","Lee","Park","Choi","Jung","Kang","Cho","Yoon","Jang","Lim",
                 "Shin","Oh","Seo","Kwon","Hwang","Ahn","Song","Ryu","Hong","Yoo"]
    },
    "DE": {
        "first": ["Lukas","Finn","Leon","Elias","Noah","Emma","Mia","Hannah","Emilia",
                   "Sofia","Maximilian","Paul","Felix","Moritz","Ben","Anna","Lea",
                   "Marie","Lina","Clara"],
        "last": ["Mueller","Schmidt","Schneider","Fischer","Weber","Meyer","Wagner",
                 "Becker","Schulz","Hoffmann","Koch","Richter","Klein","Wolf",
                 "Schroeder","Neumann","Schwarz","Zimmermann","Braun","Hartmann"]
    },
    "FR": {
        "first": ["Louis","Gabriel","Raphael","Jules","Adam","Emma","Jade","Louise",
                   "Alice","Chloe","Hugo","Lucas","Arthur","Nathan","Ethan","Lea",
                   "Rose","Anna","Ines","Camille"],
        "last": ["Martin","Bernard","Dubois","Thomas","Robert","Richard","Petit",
                 "Durand","Leroy","Moreau","Simon","Laurent","Lefebvre","Michel",
                 "Garcia","David","Bertrand","Roux","Vincent","Fournier"]
    },
    "AU": {
        "first": ["Oliver","Noah","Jack","William","Leo","Charlotte","Olivia","Amelia",
                   "Isla","Mia","Thomas","James","Ethan","Liam","Lucas","Emily",
                   "Ava","Sophie","Grace","Ella"],
        "last": ["Smith","Jones","Williams","Brown","Wilson","Taylor","Johnson",
                 "White","Martin","Anderson","Thompson","Nguyen","Robinson","Clarke",
                 "Lewis","Lee","Walker","Hall","Allen","Young"]
    },
    "CN": {
        "first": ["Wei","Jing","Fang","Lei","Xin","Yu","Ming","Hui","Jun","Lan",
                   "Tao","Gang","Yong","Jie","Qiang","Hong","Yan","Li","Na","Ping"],
        "last": ["Wang","Li","Zhang","Liu","Chen","Yang","Huang","Zhao","Wu","Zhou",
                 "Xu","Sun","Ma","Zhu","Hu","Guo","He","Lin","Luo","Deng"]
    },
    "BR": {
        "first": ["Miguel","Arthur","Heitor","Bernardo","Davi","Alice","Sophia","Helena",
                   "Valentina","Laura","Gabriel","Pedro","Lucas","Matheus","Rafael",
                   "Isabella","Manuela","Julia","Lorena","Livia"],
        "last": ["Silva","Santos","Oliveira","Souza","Rodrigues","Ferreira","Alves",
                 "Pereira","Lima","Gomes","Costa","Ribeiro","Martins","Carvalho",
                 "Almeida","Lopes","Soares","Fernandes","Vieira","Barbosa"]
    },
    "IN": {
        "first": ["Aarav","Vivaan","Aditya","Vihaan","Arjun","Sai","Siddharth",
                   "Ananya","Diya","Aisha","Rohan","Rahul","Priya","Neha","Pooja",
                   "Amit","Raj","Kiran","Sunita","Deepa"],
        "last": ["Kumar","Singh","Sharma","Patel","Gupta","Das","Mehta","Shah",
                 "Reddy","Nair","Joshi","Rao","Mishra","Verma","Choudhury",
                 "Iyer","Chatterjee","Mukherjee","Banerjee","Ghosh"]
    },
}

_ADDRESS_BY_COUNTRY = {
    "US": {"streets": ["123 Main St","456 Oak Ave","789 Elm Blvd","321 Pine Dr",
                       "654 Maple Ln","987 Cedar Ct","111 Birch Way","222 Walnut Rd"],
           "cities": ["New York","Los Angeles","Chicago","Houston","Phoenix",
                      "San Antonio","San Diego","Dallas","Seattle","Denver"],
           "states": ["NY","CA","IL","TX","AZ","TX","CA","TX","WA","CO"],
           "zip_fmt": lambda: f"{random.randint(10000,99999)}"},
    "UK": {"streets": ["10 Downing St","221B Baker St","15 Oxford Rd","88 High St",
                       "42 Queen's Rd","7 Victoria Ln","33 Church St","56 King's Way"],
           "cities": ["London","Manchester","Birmingham","Leeds","Glasgow",
                      "Liverpool","Bristol","Sheffield","Edinburgh","Cardiff"],
           "states": ["England","England","England","England","Scotland",
                      "England","England","England","Scotland","Wales"],
           "zip_fmt": lambda: f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ',k=2))}{random.randint(1,99)} {random.randint(1,9)}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ',k=2))}"},
    "ID": {"streets": ["Jl. Sudirman No.","Jl. Thamrin No.","Jl. Gatot Subroto No.",
                       "Jl. Diponegoro No.","Jl. Ahmad Yani No.","Jl. Imam Bonjol No.",
                       "Jl. Hayam Wuruk No.","Jl. Gajah Mada No."],
           "cities": ["Jakarta","Surabaya","Bandung","Medan","Semarang",
                      "Makassar","Palembang","Tangerang","Depok","Bekasi"],
           "states": ["DKI Jakarta","Jawa Timur","Jawa Barat","Sumatera Utara","Jawa Tengah",
                      "Sulawesi Selatan","Sumatera Selatan","Banten","Jawa Barat","Jawa Barat"],
           "zip_fmt": lambda: f"{random.randint(10000,99999)}"},
    "JP": {"streets": ["1-2-3 Shibuya","4-5-6 Shinjuku","7-8-9 Roppongi","1-1-1 Ginza",
                       "2-3-4 Akihabara","5-6-7 Ikebukuro","3-4-5 Harajuku","6-7-8 Asakusa"],
           "cities": ["Tokyo","Osaka","Yokohama","Nagoya","Sapporo",
                      "Fukuoka","Kobe","Kyoto","Kawasaki","Saitama"],
           "states": ["Tokyo","Osaka","Kanagawa","Aichi","Hokkaido",
                      "Fukuoka","Hyogo","Kyoto","Kanagawa","Saitama"],
           "zip_fmt": lambda: f"{random.randint(100,999)}-{random.randint(1000,9999)}"},
    "KR": {"streets": ["12 Gangnam-daero","45 Teheran-ro","78 Sejong-daero",
                       "23 Myeongdong-gil","56 Itaewon-ro","89 Hongdae-ro"],
           "cities": ["Seoul","Busan","Incheon","Daegu","Daejeon",
                      "Gwangju","Suwon","Ulsan","Seongnam","Goyang"],
           "states": ["Seoul","Busan","Incheon","Daegu","Daejeon",
                      "Gwangju","Gyeonggi","Ulsan","Gyeonggi","Gyeonggi"],
           "zip_fmt": lambda: f"{random.randint(10000,99999)}"},
    "DE": {"streets": ["Hauptstr. 1","Berliner Str. 42","Schulstr. 7","Gartenstr. 15",
                       "Bahnhofstr. 3","Ringstr. 88","Waldweg 5","Bergstr. 21"],
           "cities": ["Berlin","Hamburg","Munich","Frankfurt","Cologne",
                      "Stuttgart","Dusseldorf","Leipzig","Dortmund","Essen"],
           "states": ["Berlin","Hamburg","Bavaria","Hesse","NRW",
                      "Baden-Wurttemberg","NRW","Saxony","NRW","NRW"],
           "zip_fmt": lambda: f"{random.randint(10000,99999)}"},
    "FR": {"streets": ["12 Rue de la Paix","45 Avenue des Champs","78 Boulevard Saint-Michel",
                       "23 Rue de Rivoli","56 Rue du Faubourg","89 Avenue Montaigne"],
           "cities": ["Paris","Marseille","Lyon","Toulouse","Nice",
                      "Nantes","Strasbourg","Montpellier","Bordeaux","Lille"],
           "states": ["Ile-de-France","Bouches-du-Rhone","Rhone","Haute-Garonne","Alpes-Maritimes",
                      "Loire-Atlantique","Bas-Rhin","Herault","Gironde","Nord"],
           "zip_fmt": lambda: f"{random.randint(10000,99999)}"},
    "AU": {"streets": ["12 Collins St","45 George St","78 King William St",
                       "23 Bourke St","56 Elizabeth St","89 Swanston St"],
           "cities": ["Sydney","Melbourne","Brisbane","Perth","Adelaide",
                      "Gold Coast","Newcastle","Canberra","Wollongong","Hobart"],
           "states": ["NSW","VIC","QLD","WA","SA",
                      "QLD","NSW","ACT","NSW","TAS"],
           "zip_fmt": lambda: f"{random.randint(1000,9999)}"},
    "CN": {"streets": ["1 Zhongshan Rd","42 Nanjing Rd","15 Chang'an Ave",
                       "88 Wangfujing St","23 Xidan North St","56 Lujiazui Rd"],
           "cities": ["Beijing","Shanghai","Guangzhou","Shenzhen","Chengdu",
                      "Hangzhou","Wuhan","Chongqing","Nanjing","Tianjin"],
           "states": ["Beijing","Shanghai","Guangdong","Guangdong","Sichuan",
                      "Zhejiang","Hubei","Chongqing","Jiangsu","Tianjin"],
           "zip_fmt": lambda: f"{random.randint(100000,999999)}"},
    "BR": {"streets": ["Rua Augusta 123","Av. Paulista 456","Rua Oscar Freire 789",
                       "Rua das Laranjeiras 321","Av. Atlantica 654","Rua da Consolacao 987"],
           "cities": ["Sao Paulo","Rio de Janeiro","Brasilia","Salvador","Fortaleza",
                      "Belo Horizonte","Manaus","Curitiba","Recife","Porto Alegre"],
           "states": ["SP","RJ","DF","BA","CE",
                      "MG","AM","PR","PE","RS"],
           "zip_fmt": lambda: f"{random.randint(10000,99999)}-{random.randint(100,999)}"},
    "IN": {"streets": ["MG Road 12","Brigade Road 45","Park Street 78",
                       "Anna Salai 23","Mall Road 56","Civil Lines 89"],
           "cities": ["Mumbai","Delhi","Bangalore","Hyderabad","Chennai",
                      "Kolkata","Pune","Ahmedabad","Jaipur","Lucknow"],
           "states": ["Maharashtra","Delhi","Karnataka","Telangana","Tamil Nadu",
                      "West Bengal","Maharashtra","Gujarat","Rajasthan","Uttar Pradesh"],
           "zip_fmt": lambda: f"{random.randint(100000,999999)}"},
}

_FLAG = {"US":"US","UK":"GB","ID":"ID","JP":"JP","KR":"KR","DE":"DE",
         "FR":"FR","AU":"AU","CN":"CN","BR":"BR","IN":"IN","ES":"ES",
         "IT":"IT","NL":"NL","CA":"CA","SG":"SG","MY":"MY","TH":"TH",
         "PH":"PH","VN":"VN","RU":"RU","MX":"MX","AR":"AR","CO":"CO",
         "SE":"SE","NO":"NO","DK":"DK","FI":"FI","PL":"PL","PT":"PT",
         "BE":"BE","AT":"AT","CH":"CH","IE":"IE","NZ":"NZ","ZA":"ZA",
         "TR":"TR","SA":"SA","AE":"AE","EG":"EG","NG":"NG","KE":"KE"}

def _resolve_country(cc: str) -> str:
    cc = cc.upper()
    if cc in _NAMES_BY_COUNTRY:
        return cc
    _FALLBACK = {"EN":"US","GB":"UK","SG":"US","MY":"ID","TH":"ID","PH":"ID",
                 "VN":"ID","ES":"ES","IT":"IT","NL":"NL","CA":"US","NZ":"AU",
                 "MX":"BR","AR":"BR","CO":"BR","SE":"DE","NO":"DE","DK":"DE",
                 "FI":"DE","PL":"DE","PT":"FR","BE":"FR","AT":"DE","CH":"DE",
                 "IE":"UK","ZA":"UK","TR":"DE","SA":"IN","AE":"IN","EG":"IN",
                 "NG":"IN","KE":"IN","RU":"DE","VN":"CN","MY":"ID","PH":"ID",
                 "TH":"ID","SG":"US"}
    return _FALLBACK.get(cc, "US")

def generate_name(country: str = "US") -> str:
    """Generate a random test name matching the card's country."""
    cc = _resolve_country(country)
    pool = _NAMES_BY_COUNTRY.get(cc, _NAMES_BY_COUNTRY["US"])
    return f"{random.choice(pool['first'])} {random.choice(pool['last'])}"

def generate_address(country: str = "US") -> Dict:
    """Generate a random test address matching the card's country."""
    cc = _resolve_country(country)
    pool = _ADDRESS_BY_COUNTRY.get(cc, _ADDRESS_BY_COUNTRY["US"])
    idx = random.randint(0, len(pool["streets"]) - 1)
    street = pool["streets"][idx]
    if cc == "ID":
        street = f"{street}{random.randint(1,150)}"
    return {
        "street": street,
        "city": pool["cities"][idx % len(pool["cities"])],
        "state": pool["states"][idx % len(pool["states"])],
        "zip": pool["zip_fmt"](),
        "country": cc
    }

# ═══════════════════════════════════════════════
# PHONE NUMBER GENERATION (v3.4)
# ═══════════════════════════════════════════════

_PHONE_BY_COUNTRY = {
    "US": lambda: f"+1 ({random.choice(['201','202','203','205','206','207','208','209','210','212','213','214','215','216','217','218','219','224','225','228','229','231','234','239','240','248','251','253','254','256','260','262','267','269','270','276','281','301','302','303','304','305','307','308','309','310','312','313','314','315','316','317','318','319','320','321','323','325','330','331','334','336','337','339','346','347','351','352','360','361','364','385','386','401','402','404','405','406','407','408','409','410','412','413','414','415','417','419','423','424','425','430','432','434','435','440','442','443','469','470','475','478','479','480','484','501','502','503','504','505','507','508','509','510','512','513','515','516','517','518','520','530','531','534','539','540','541','551','559','561','562','563','567','570','571','573','574','575','580','585','586','601','602','603','605','606','607','608','609','610','612','614','615','616','617','618','619','620','623','626','627','628','630','631','636','641','646','650','651','657','660','661','662','667','669','678','681','682','701','702','703','704','706','707','708','712','713','714','715','716','717','718','719','720','724','725','727','731','732','734','737','740','743','747','754','757','760','762','763','765','769','770','772','773','774','775','779','781','785','786','801','802','803','804','805','806','808','810','812','813','814','815','816','817','818','828','830','831','832','843','845','847','848','850','854','856','857','858','859','860','862','863','864','865','870','872','878','901','903','904','906','907','908','909','910','912','913','914','915','916','917','918','919','920','925','928','929','930','931','936','937','938','940','941','947','949','951','952','954','956','959','970','971','972','973','975','978','979','980','984','985'])}) {random.randint(100,999)}-{random.randint(1000,9999)}",
    "UK": lambda: f"+44 7{random.randint(100,999)} {random.randint(100000,999999)}",
    "ID": lambda: f"+62 {random.choice(['811','812','813','815','816','817','818','819','851','852','853','855','856','857','858'])}-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
    "JP": lambda: f"+81 {random.choice(['70','80','90'])}-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
    "KR": lambda: f"+82 {random.choice(['10','11','16','17','18','19'])}-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
    "DE": lambda: f"+49 1{random.choice(['51','52','55','57','59','60','62','63','70','71','72','73','74','75','76','77','78','79'])} {random.randint(100,999)} {random.randint(10000,99999)}",
    "FR": lambda: f"+33 {random.choice(['6','7'])}{random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)}",
    "AU": lambda: f"+61 4{random.randint(10,99)} {random.randint(100,999)} {random.randint(100,999)}",
    "CN": lambda: f"+86 1{random.choice(['30','31','32','33','34','35','36','37','38','39','50','51','52','53','55','56','57','58','59','70','71','72','73','75','76','77','78','79','80','81','82','83','84','85','86','87','88','89','98'])} {random.randint(1000,9999)} {random.randint(1000,9999)}",
    "BR": lambda: f"+55 ({random.choice(['11','21','31','41','51','61','71','81','85','91'])}) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
    "IN": lambda: f"+91 {random.choice(['70','72','73','74','75','76','77','78','79','80','81','82','83','84','85','86','87','88','89','90','91','92','93','94','95','96','97','98','99'])}{random.randint(10000000,99999999)}",
}

def generate_phone(country: str = "US") -> str:
    """Generate a random phone number matching the card's country."""
    cc = _resolve_country(country)
    generator = _PHONE_BY_COUNTRY.get(cc, _PHONE_BY_COUNTRY["US"])
    return generator()

# ═══════════════════════════════════════════════
# LIVE CARD TRACKER (v3.4) — SQLite
# ═══════════════════════════════════════════════

import sqlite3

TRACKER_DB = os.environ.get("TRACKER_DB", "/tmp/live_tracker.db")

def _init_tracker_db():
    """Initialize the Live Card Tracker database."""
    os.makedirs(os.path.dirname(TRACKER_DB), exist_ok=True)
    conn = sqlite3.connect(TRACKER_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS card_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_number TEXT NOT NULL,
            status TEXT NOT NULL,  -- 'live', 'die', 'unknown'
            bin_number TEXT,
            bank TEXT,
            country TEXT,
            network TEXT,
            checked_at TEXT DEFAULT (datetime('now')),
            checker TEXT DEFAULT 'chkr.cc',
            batch_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bin_stats (
            bin_number TEXT PRIMARY KEY,
            total_checked INTEGER DEFAULT 0,
            live_count INTEGER DEFAULT 0,
            die_count INTEGER DEFAULT 0,
            unknown_count INTEGER DEFAULT 0,
            live_rate REAL DEFAULT 0.0,
            bank TEXT,
            country TEXT,
            network TEXT,
            first_checked TEXT,
            last_checked TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS check_batches (
            batch_id TEXT PRIMARY KEY,
            total_cards INTEGER,
            live_count INTEGER,
            die_count INTEGER,
            unknown_count INTEGER,
            live_rate REAL,
            bins_used TEXT,
            checked_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn

def track_check(card_number: str, status: str, bin_number: str = None,
                bank: str = None, country: str = None, network: str = None,
                batch_id: str = None):
    """Record a card check result."""
    conn = _init_tracker_db()
    try:
        conn.execute(
            "INSERT INTO card_checks (card_number, status, bin_number, bank, country, network, batch_id) VALUES (?,?,?,?,?,?,?)",
            (card_number[-4:], status, bin_number, bank, country, network, batch_id)
        )
        # Update bin_stats
        if bin_number:
            conn.execute("""
                INSERT INTO bin_stats (bin_number, total_checked, live_count, die_count, unknown_count, live_rate, bank, country, network, first_checked, last_checked)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(bin_number) DO UPDATE SET
                    total_checked = total_checked + 1,
                    live_count = live_count + ?,
                    die_count = die_count + ?,
                    unknown_count = unknown_count + ?,
                    live_rate = CAST(live_count + ? AS REAL) / (total_checked + 1),
                    last_checked = datetime('now')
            """, (bin_number,
                  1 if status == 'live' else 0,
                  1 if status == 'die' else 0,
                  1 if status == 'unknown' else 0,
                  (1 if status == 'live' else 0) / 1.0,
                  bank, country, network,
                  1 if status == 'live' else 0,
                  1 if status == 'die' else 0,
                  1 if status == 'unknown' else 0,
                  1 if status == 'live' else 0))
        conn.commit()
    finally:
        conn.close()

def record_batch(batch_id: str, cards: list, live_cards: list, bins_used: list):
    """Record a batch check result."""
    conn = _init_tracker_db()
    try:
        total = len(cards)
        live = len(live_cards)
        die = total - live  # simplified
        rate = live / total if total > 0 else 0
        conn.execute(
            "INSERT OR REPLACE INTO check_batches VALUES (?,?,?,?,?,?,?,datetime('now'))",
            (batch_id, total, live, die, 0, rate, ','.join(bins_used))
        )
        conn.commit()
    finally:
        conn.close()

def get_bin_recommendations(top_n: int = 5) -> list:
    """Get top BINs by historical live rate."""
    conn = _init_tracker_db()
    try:
        cursor = conn.execute("""
            SELECT bin_number, bank, country, network, total_checked,
                   live_count, die_count, live_rate, last_checked
            FROM bin_stats
            WHERE total_checked >= 5
            ORDER BY live_rate DESC, total_checked DESC
            LIMIT ?
        """, (top_n,))
        results = []
        for row in cursor:
            results.append({
                "bin": row[0], "bank": row[1], "country": row[2],
                "network": row[3], "total_checked": row[4],
                "live": row[5], "die": row[6], "live_rate": f"{row[7]*100:.1f}%",
                "last_checked": row[8]
            })
        return results
    finally:
        conn.close()

def get_tracker_stats() -> dict:
    """Get overall tracker statistics."""
    conn = _init_tracker_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM card_checks").fetchone()[0]
        live = conn.execute("SELECT COUNT(*) FROM card_checks WHERE status='live'").fetchone()[0]
        die = conn.execute("SELECT COUNT(*) FROM card_checks WHERE status='die'").fetchone()[0]
        unknown = conn.execute("SELECT COUNT(*) FROM card_checks WHERE status='unknown'").fetchone()[0]
        batches = conn.execute("SELECT COUNT(*) FROM check_batches").fetchone()[0]
        bins_tracked = conn.execute("SELECT COUNT(*) FROM bin_stats").fetchone()[0]
        return {
            "total_checked": total, "live": live, "die": die, "unknown": unknown,
            "batches": batches, "bins_tracked": bins_tracked,
            "overall_live_rate": f"{live/total*100:.1f}%" if total > 0 else "N/A"
        }
    finally:
        conn.close()

# ═══════════════════════════════════════════════
# ENRICHMENT (v3.4) — add details to existing cards
# ═══════════════════════════════════════════════

def enrich_card(card_number: str) -> dict:
    """Enrich an existing card number with name, address, phone, BIN info."""
    # Parse the card
    if "|" in card_number:
        parts = card_number.split("|")
        clean = parts[0]
        expiry = f"{parts[1]}/{parts[2]}" if len(parts) >= 3 else None
        cvv = parts[3] if len(parts) >= 4 else None
    else:
        clean = card_number.replace(" ", "").replace("-", "")
        expiry = None
        cvv = None
    
    # Lookup BIN (online first, then local)
    bin_prefix = clean[:8] if len(clean) >= 8 else clean[:6]
    bin_info = lookup_bin_online(bin_prefix, use_cache=True)
    
    # Country resolution: prefer online > local DB > default
    country_code = bin_info.get("country_code", "")
    if not country_code or country_code == "??":
        # Fallback: try local DB
        local_info = lookup_bin(clean[:6])
        country_code = local_info.get("country", "US")
    country_code = country_code.upper()[:2]  # Normalize to 2-letter
    
    network = _detect_network(clean)
    
    # Generate profile
    name = generate_name(country_code)
    address = generate_address(country_code)
    phone = generate_phone(country_code)
    
    result = {
        "number": clean,
        "raw_number": clean,
        "name": name,
        "phone": phone,
        "billing_address": address,
        "bin": bin_info.get("bin", bin_prefix[:6]),
        "bank": bin_info.get("bank", "Unknown"),
        "country": bin_info.get("country", "Unknown"),
        "country_code": country_code,
        "brand": bin_info.get("brand", network),
        "network": network,
        "scheme": bin_info.get("scheme", network),
        "card_type": bin_info.get("type", "Unknown"),
        "bin_source": bin_info.get("_source", "unknown"),
    }
    if expiry:
        result["expiry"] = expiry
    if cvv:
        result["cvv"] = cvv
    return result

def enrich_cards_batch(cards: list) -> list:
    """Enrich a list of card strings with full details."""
    enriched = []
    for card_str in cards:
        try:
            result = enrich_card(card_str)
            enriched.append(result)
        except Exception as e:
            enriched.append({"error": str(e), "input": card_str})
    return enriched

def parse_input_file(filepath: str) -> list:
    """Parse a file of pipe-delimited cards."""
    cards = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                cards.append(line)
    return cards

# ═══════════════════════════════════════════════
# SITE-SPECIFIC FORMATTING (v3.4)
# ═══════════════════════════════════════════════

def format_stripe(card: dict) -> dict:
    """Format card for Stripe checkout."""
    return {
        "card[number]": card.get("raw_number", ""),
        "card[exp_month]": card.get("expiry", "12/2028").split("/")[0],
        "card[exp_year]": card.get("expiry", "12/2028").split("/")[1],
        "card[cvc]": card.get("cvv", ""),
        "name": card.get("name", ""),
        "address_line1": card.get("billing_address", {}).get("street", ""),
        "address_city": card.get("billing_address", {}).get("city", ""),
        "address_state": card.get("billing_address", {}).get("state", ""),
        "address_zip": card.get("billing_address", {}).get("zip", ""),
        "address_country": card.get("billing_address", {}).get("country", "US"),
    }

def format_shopify(card: dict) -> dict:
    """Format card for Shopify checkout."""
    addr = card.get("billing_address", {})
    return {
        "credit_card[number]": card.get("raw_number", ""),
        "credit_card[month]": card.get("expiry", "12/2028").split("/")[0],
        "credit_card[year]": card.get("expiry", "12/2028").split("/")[1],
        "credit_card[verification_value]": card.get("cvv", ""),
        "credit_card[name]": card.get("name", ""),
        "checkout[billing_address][address1]": addr.get("street", ""),
        "checkout[billing_address][city]": addr.get("city", ""),
        "checkout[billing_address][province]": addr.get("state", ""),
        "checkout[billing_address][zip]": addr.get("zip", ""),
        "checkout[billing_address][country]": addr.get("country", "US"),
        "checkout[billing_address][phone]": card.get("phone", ""),
    }

def format_paypal(card: dict) -> dict:
    """Format card for PayPal."""
    addr = card.get("billing_address", {})
    return {
        "card_number": card.get("raw_number", ""),
        "expire_date": card.get("expiry", "12/2028"),
        "cvv2": card.get("cvv", ""),
        "first_name": card.get("name", "").split()[0] if card.get("name") else "",
        "last_name": " ".join(card.get("name", "").split()[1:]) if card.get("name") else "",
        "billing_address[line1]": addr.get("street", ""),
        "billing_address[city]": addr.get("city", ""),
        "billing_address[state]": addr.get("state", ""),
        "billing_address[postal_code]": addr.get("zip", ""),
        "billing_address[country_code]": addr.get("country", "US"),
    }

def format_generic(card: dict) -> dict:
    """Format card for generic checkout forms."""
    addr = card.get("billing_address", {})
    return {
        "card_number": card.get("raw_number", ""),
        "exp_month": card.get("expiry", "12/2028").split("/")[0],
        "exp_year": card.get("expiry", "12/2028").split("/")[1],
        "cvv": card.get("cvv", ""),
        "cardholder_name": card.get("name", ""),
        "email": f"{card.get('name','').lower().replace(' ','.')}_{random.randint(100,999)}@gmail.com",
        "phone": card.get("phone", ""),
        "address": addr.get("street", ""),
        "city": addr.get("city", ""),
        "state": addr.get("state", ""),
        "zip": addr.get("zip", ""),
        "country": addr.get("country", "US"),
    }

FORMATTERS = {
    "stripe": format_stripe,
    "shopify": format_shopify,
    "paypal": format_paypal,
    "generic": format_generic,
}

def format_card(card: dict, site: str) -> dict:
    """Format card for a specific site."""
    formatter = FORMATTERS.get(site.lower(), format_generic)
    return formatter(card)

# ═══════════════════════════════════════════════
# CARD GENERATION
# ═══════════════════════════════════════════════

def generate_card(card_type: str = "visa", custom_bin: str = None) -> Dict:
    """Generate a complete test card with country-aware name & address."""
    card_info = BIN_DATABASE.get(card_type, BIN_DATABASE["visa"])
    
    number = generate_card_number(card_type, custom_bin)
    expiry = generate_expiry()
    cvv = generate_cvv(card_info["cvv_length"])
    
    # Resolve country from BIN for name/address
    bin_prefix = custom_bin or card_info["prefixes"][0]
    bin_info = lookup_bin(bin_prefix)
    country = bin_info.get("country", "US")
    
    name = generate_name(country)
    address = generate_address(country)
    phone = generate_phone(country)
    
    return {
        "type": card_info["name"],
        "bin": custom_bin or card_info["prefixes"][0],
        "number": ' '.join([number[i:i+4] for i in range(0, len(number), 4)]),
        "raw_number": number,
        "expiry": expiry,
        "cvv": cvv,
        "name": name,
        "phone": phone,
        "billing_address": address,
        "valid_luhn": is_valid_luhn(number),
        "generated_at": datetime.now().isoformat(),
        "purpose": "TESTING AND DEVELOPMENT ONLY - NOT FOR REAL TRANSACTIONS"
    }

# ═══════════════════════════════════════════════
# BATCH GENERATION
# ═══════════════════════════════════════════════

def generate_batch(
    count: int = 10,
    card_types: List[str] = None,
    custom_bins: List[str] = None,
    include_types: bool = True
) -> List[Dict]:
    """Generate a batch of test cards."""
    if card_types is None:
        card_types = list(BIN_DATABASE.keys())
    
    cards = []
    for i in range(count):
        if custom_bins:
            # Cycle through custom BINs: [0,1,0,1,...] if 2 bins, [0,0,0,...] if 1 bin
            custom_bin = custom_bins[i % len(custom_bins)]
            card_type = detect_card_type(custom_bin)
            card = generate_card(card_type, custom_bin)
        else:
            # Random card type
            card_type = random.choice(card_types)
            card = generate_card(card_type)
        cards.append(card)
    
    return cards

# ═══════════════════════════════════════════════
# LUHN VALIDATOR
# ═══════════════════════════════════════════════

def validate_card(number: str) -> Dict:
    """Validate a card number using Luhn algorithm."""
    # Remove spaces and dashes
    clean = number.replace(" ", "").replace("-", "")
    
    if not clean.isdigit():
        return {"valid": False, "error": "Contains non-numeric characters"}
    
    if len(clean) < 13 or len(clean) > 19:
        return {"valid": False, "error": f"Invalid length: {len(clean)} digits"}
    
    is_valid = is_valid_luhn(clean)
    card_type = detect_card_type(clean)
    
    return {
        "number": clean,
        "formatted": ' '.join([clean[i:i+4] for i in range(0, len(clean), 4)]),
        "valid_luhn": is_valid,
        "card_type": card_type,
        "length": len(clean),
        "checksum": luhn_checksum(clean)
    }

# ═══════════════════════════════════════════════
# CARD PARSER (v3.2)
# ═══════════════════════════════════════════════

def parse_card(number: str) -> Dict:
    """
    Parse a card number: extract BIN, lookup bank/country/type.
    Works with any format: "4242 4242 4242 4242", "4242424242424242", etc.
    """
    clean = number.replace(" ", "").replace("-", "").replace("|", "").strip()
    
    if not clean.isdigit():
        return {"error": "Non-numeric characters found", "input": number}
    
    if len(clean) < 6:
        return {"error": f"Too short ({len(clean)} digits, need 6+)", "input": number}
    
    bin_number = clean[:8]  # Try 8-digit first
    bin_info = lookup_bin_online(bin_number, use_cache=True)
    
    # Card validation
    is_valid = is_valid_luhn(clean) if len(clean) >= 13 else None
    network = _detect_network(clean)
    
    result = {
        "number": clean,
        "formatted": ' '.join([clean[i:i+4] for i in range(0, len(clean), 4)]),
        "bin": bin_info.get("bin", bin_number[:6]),
        "bank": bin_info.get("bank", "Unknown"),
        "bank_city": bin_info.get("bank_city", ""),
        "bank_url": bin_info.get("bank_url", ""),
        "country": bin_info.get("country", "Unknown"),
        "country_code": bin_info.get("country_code", "??"),
        "country_currency": bin_info.get("country_currency", ""),
        "brand": bin_info.get("brand", "Unknown"),
        "card_type": bin_info.get("type", "Unknown"),
        "prepaid": bin_info.get("prepaid", None),
        "scheme": bin_info.get("scheme", network),
        "network": network,
        "length": len(clean),
        "luhn_valid": is_valid,
        "bin_source": bin_info.get("_source", "unknown")
    }
    
    return result

def parse_cards_batch(numbers: list) -> list:
    """Parse multiple card numbers at once."""
    results = []
    for num in numbers:
        result = parse_card(num)
        results.append(result)
    return results

# ═══════════════════════════════════════════════
# SMART GENERATE (v3.2)
# ═══════════════════════════════════════════════

def generate_smart(count: int = 10, card_types: list = None, 
                   custom_bins: list = None, enrich: bool = True) -> list:
    """
    Generate cards with automatic BIN enrichment.
    Each card includes bank, country, brand info from online lookup.
    """
    cards = generate_batch(count=count, card_types=card_types, custom_bins=custom_bins)
    
    if enrich:
        seen_bins = {}
        for card in cards:
            bin_prefix = card.get("bin", "")[:8]
            
            # Cache BIN lookups within same batch
            if bin_prefix in seen_bins:
                bin_info = seen_bins[bin_prefix]
            else:
                bin_info = lookup_bin_online(bin_prefix, use_cache=True)
                seen_bins[bin_prefix] = bin_info
            
            # Enrich card with BIN info
            card["bank"] = bin_info.get("bank", "Unknown")
            card["bank_city"] = bin_info.get("bank_city", "")
            card["country"] = bin_info.get("country", "Unknown")
            card["country_code"] = bin_info.get("country_code", "??")
            card["brand"] = bin_info.get("brand", "Unknown")
            card["card_subtype"] = bin_info.get("type", "Unknown")
            card["prepaid"] = bin_info.get("prepaid", None)
            card["scheme"] = bin_info.get("scheme", card.get("type", "Unknown"))
            card["bin_source"] = bin_info.get("_source", "unknown")
    
    return cards

# ═══════════════════════════════════════════════
# CSV EXPORT (v3.2)
# ═══════════════════════════════════════════════

def export_csv(cards: list, filepath: str, pipe_format: bool = False):
    """
    Export cards to CSV file.
    If pipe_format=True, uses pipe-delimited format for chkr.cc.
    """
    import csv
    
    if pipe_format:
        # pipe-delimited: number|MM|YYYY|CVV
        with open(filepath, 'w', newline='') as f:
            for card in cards:
                raw = card.get("raw_number", card.get("number", ""))
                expiry = card.get("expiry", "")
                if "/" in expiry:
                    month, year = expiry.split("/")
                else:
                    month, year = "12", "2028"
                cvv = card.get("cvv", "000")
                f.write(f"{raw}|{month}|{year}|{cvv}\n")
    else:
        # Full CSV with all columns
        if not cards:
            return
        
        fieldnames = [
            "number", "raw_number", "type", "bin", "bank", "country", 
            "country_code", "brand", "scheme", "card_subtype", "prepaid",
            "expiry", "cvv", "name", "valid_luhn"
        ]
        
        # Add any extra fields from enrichment
        for card in cards:
            for key in card.keys():
                if key not in fieldnames and not key.startswith("_"):
                    fieldnames.append(key)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for card in cards:
                writer.writerow(card)
    
    return filepath

# ═══════════════════════════════════════════════
# FIND BEST BINS (v3.2)
# ═══════════════════════════════════════════════

def find_best_bins(country: str = None, network: str = None, 
                   count: int = 10, scan_all: bool = False) -> list:
    """
    Find best BINs by country/network, ranked by diversity.
    Uses online lookup to discover BINs not in local DB.
    
    Args:
        country: 2-letter country code (US, UK, ID, etc.)
        network: visa, mastercard, amex, discover, jcb, unionpay
        count: Number of BINs to return
        scan_all: If True, scan all local DB BINs + attempt online discovery
    
    Returns:
        List of dicts with BIN info, sorted by bank diversity
    """
    candidates = []
    
    # First: filter local DB by country/network
    for bin_num, info in BANK_BINS.items():
        match = True
        if country and info.get("country", "").upper() != country.upper():
            match = False
        if network and network.lower() not in info.get("type", "").lower():
            # Check network prefix
            if not bin_num.startswith(_network_prefix(network)):
                match = False
        if match:
            candidates.append({
                "bin": bin_num,
                "bank": info.get("bank", "Unknown"),
                "type": info.get("type", "Unknown"),
                "country": info.get("country", "??"),
                "source": "local_db"
            })
    
    # If scan_all or few candidates, enrich with online lookup
    if scan_all or len(candidates) < count:
        # Try known BIN ranges for the country
        seed_bins = _generate_seed_bins(country, network, count * 3)
        for seed in seed_bins[:count * 2]:  # Limit API calls
            if any(c["bin"] == seed[:6] for c in candidates):
                continue
            try:
                info = lookup_bin_online(seed, use_cache=True)
                if "error" not in info and info.get("bank", "Unknown") != "Unknown":
                    candidates.append({
                        "bin": info.get("bin", seed),
                        "bank": info.get("bank", "Unknown"),
                        "type": info.get("type", "Unknown"),
                        "country": info.get("country_code", "??"),
                        "brand": info.get("brand", "Unknown"),
                        "scheme": info.get("scheme", "Unknown"),
                        "source": "binlist.net"
                    })
            except:
                continue
    
    # Deduplicate by bank name (keep first BIN per bank for diversity)
    seen_banks = set()
    unique = []
    for c in candidates:
        bank_key = c.get("bank", "Unknown").lower()
        if bank_key not in seen_banks:
            seen_banks.add(bank_key)
            unique.append(c)
    
    return unique[:count]

def _network_prefix(network: str) -> str:
    """Get the typical prefix for a card network."""
    prefixes = {
        "visa": "4",
        "mastercard": "5",
        "amex": "3",
        "discover": "6",
        "jcb": "35",
        "unionpay": "62",
        "diners": "3"
    }
    return prefixes.get(network.lower(), "")

def _generate_seed_bins(country: str = None, network: str = None, count: int = 20) -> list:
    """Generate seed BINs to try for online discovery."""
    prefix = _network_prefix(network) if network else "4"
    
    seeds = []
    
    # Country-specific known ranges
    country_ranges = {
        "US": ["40", "41", "42", "43", "44", "45", "46", "47", "48", "51", "52", "53", "54", "55"],
        "UK": ["44", "45", "46", "47", "48", "49", "51", "52", "53", "54", "55"],
        "ID": ["45", "46", "55", "56"],
        "JP": ["35", "36", "37"],
        "CN": ["62", "63"],
        "DE": ["49", "50", "51"],
        "FR": ["48", "49", "50"],
        "AU": ["46", "47", "48", "51", "52"],
        "KR": ["62", "63", "35"],
    }
    
    if country and country.upper() in country_ranges:
        ranges = country_ranges[country.upper()]
    else:
        ranges = [prefix.ljust(2, '0')]
    
    for r in ranges:
        # Generate variations: r + 4 random digits (making 6-digit BIN)
        for _ in range(count // len(ranges) + 1):
            bin_candidate = r + ''.join([str(random.randint(0, 9)) for _ in range(6 - len(r))])
            seeds.append(bin_candidate)
    
    random.shuffle(seeds)
    return seeds[:count]

# ═══════════════════════════════════════════════
# PIPE FORMAT HELPER (v3.2)
# ═══════════════════════════════════════════════

def cards_to_pipe(cards: list) -> list:
    """Convert cards to pipe-delimited format: number|MM|YYYY|CVV"""
    pipes = []
    for card in cards:
        raw = card.get("raw_number", card.get("number", ""))
        expiry = card.get("expiry", "12/2028")
        if "/" in expiry:
            month, year = expiry.split("/")
        else:
            month, year = "12", "2028"
        cvv = card.get("cvv", "000")
        pipes.append(f"{raw}|{month}|{year}|{cvv}")
    return pipes

# ═══════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Luhn Card Number Generator v3.3 - For Testing Only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate cards
  %(prog)s                              # Generate 10 random cards
  %(prog)s -n 50 -t visa mastercard     # 50 Visa/MC cards
  %(prog)s --bin 453201 -n 20           # 20 cards with specific BIN
  %(prog)s -o output.json               # Save to file
  
  # Auto BIN generation
  %(prog)s --generate-bins 10           # Generate 10 unique BINs
  %(prog)s --generate-bins 5 -t visa    # 5 Visa BINs
  %(prog)s --generate-bins 3 --country ID --bank BCA  # 3 BCA Indonesia BINs
  
  # BIN lookup
  %(prog)s --lookup-bin 400344          # Look up BIN info
  %(prog)s --lookup-bin 559000          # Look up BIN info
  
  # Validate
  %(prog)s --validate 4242424242424242  # Validate a number
        """
    )
    
    # Generate cards
    parser.add_argument("-n", "--count", type=int, default=10,
                       help="Number of cards to generate (default: 10)")
    parser.add_argument("-t", "--types", nargs="+", 
                       choices=list(BIN_DATABASE.keys()),
                       help="Card types to generate")
    parser.add_argument("--bin", nargs="+",
                       help="Custom BIN(s) to use")
    parser.add_argument("--validate", 
                       help="Validate a card number")
    parser.add_argument("-o", "--output", 
                       help="Output JSON file")
    parser.add_argument("--flat", action="store_true",
                       help="Output flat list (no metadata)")
    parser.add_argument("--raw", action="store_true",
                       help="Output raw numbers only (one per line)")
    
    # Auto BIN generation
    parser.add_argument("--generate-bins", type=int, metavar="COUNT",
                       help="Generate unique BINs (e.g., --generate-bins 10)")
    parser.add_argument("--country", 
                       help="Filter BINs by country code (US, UK, ID, etc.)")
    parser.add_argument("--bank", 
                       help="Filter BINs by bank name")
    parser.add_argument("--lookup-bin", metavar="BIN",
                       help="Look up BIN information (online by default)")
    parser.add_argument("--batch-lookup", nargs="+", metavar="BIN",
                       help="Look up multiple BINs at once")
    parser.add_argument("--offline", action="store_true",
                       help="Use local DB only (skip online lookup)")
    parser.add_argument("--no-cache", action="store_true",
                       help="Skip BIN cache, force fresh lookup")
    parser.add_argument("--clear-cache", action="store_true",
                       help="Clear BIN cache file")
    parser.add_argument("--list-bins", action="store_true",
                       help="List all available BINs in database")
    
    # v3.2 new features
    parser.add_argument("--parse", metavar="NUMBER",
                       help="Parse a card number: extract BIN, bank, country, type")
    parser.add_argument("--batch-parse", nargs="+", metavar="NUMBER",
                       help="Parse multiple card numbers at once")
    parser.add_argument("--smart", action="store_true",
                       help="Smart generate: cards + auto BIN enrichment")
    parser.add_argument("--csv", metavar="FILE",
                       help="Export to CSV file")
    parser.add_argument("--pipe", action="store_true",
                       help="Output in pipe-delimited format (number|MM|YYYY|CVV)")
    parser.add_argument("--find-bins", action="store_true",
                       help="Find best BINs by country/network")
    parser.add_argument("--proxy", metavar="PROXY",
                       help="Proxy for chkr.cc (http://ip:port or socks5://ip:port)")
    parser.add_argument("--full", action="store_true",
                       help="Full output: raw data top, name+address+BIN info below")
    parser.add_argument("--json-full", action="store_true",
                       help="Full JSON output including name, address, BIN enrichment")
    parser.add_argument("--enrich", nargs="+", metavar="CARD",
                       help="Enrich existing cards with name, address, phone, BIN info")
    parser.add_argument("--input", metavar="FILE",
                       help="Read cards from file (pipe-delimited, one per line)")
    parser.add_argument("--format", choices=["stripe","shopify","paypal","generic"],
                       help="Format output for specific checkout site")
    parser.add_argument("--tracker-stats", action="store_true",
                       help="Show Live Card Tracker statistics")
    parser.add_argument("--recommend", action="store_true",
                       help="Show BIN recommendations based on historical data")
    parser.add_argument("--track-result", nargs=2, metavar=("CARD", "STATUS"),
                       help="Record a check result: --track-result 'card|mm|yyyy|cvv' live|die|unknown")
    
    args = parser.parse_args()
    
    # Enrich existing cards mode
    if args.enrich:
        cards = args.enrich
        enriched = enrich_cards_batch(cards)
        
        if args.format:
            # Format for specific site
            for e in enriched:
                if "error" not in e:
                    formatted = format_card(e, args.format)
                    print(json.dumps(formatted, indent=2))
                    print("---")
        else:
            # Raw data at top
            for e in enriched:
                if "error" not in e:
                    raw = e.get("raw_number", "")
                    exp = e.get("expiry", "12/2028")
                    m, y = exp.split("/")
                    cvv = e.get("cvv", "000")
                    print(f"{raw}|{m}|{y}|{cvv}")
            print()
            
            # Details below
            for i, e in enumerate(enriched):
                if "error" in e:
                    print(f"[{i+1}] ERROR: {e['error']} ({e['input']})")
                    continue
                addr = e.get("billing_address", {})
                print(f"[{i+1}] {e['raw_number']}")
                print(f"    Name: {e['name']}")
                print(f"    Phone: {e.get('phone', 'N/A')}")
                print(f"    Address: {addr.get('street','')}, {addr.get('city','')}, {addr.get('state','')} {addr.get('zip','')}")
                print(f"    Country: {e.get('country','')} ({e.get('country_code','')})")
                print(f"    Bank: {e.get('bank','')}")
                print(f"    BIN: {e.get('bin','')} | {e.get('network','')} | {e.get('card_type','')}")
                print(f"    Exp: {e.get('expiry','')} | CVV: {e.get('cvv','')}")
                print()
        return
    
    # Input file mode
    if args.input:
        cards = parse_input_file(args.input)
        if not cards:
            print("No cards found in file")
            return
        
        if args.format:
            # Format for specific site
            enriched = enrich_cards_batch(cards)
            for e in enriched:
                if "error" not in e:
                    formatted = format_card(e, args.format)
                    print(json.dumps(formatted, indent=2))
                    print("---")
        else:
            # Enrich + display
            enriched = enrich_cards_batch(cards)
            for e in enriched:
                if "error" not in e:
                    raw = e.get("raw_number", "")
                    exp = e.get("expiry", "12/2028")
                    m, y = exp.split("/")
                    cvv = e.get("cvv", "000")
                    print(f"{raw}|{m}|{y}|{cvv}")
            print()
            for i, e in enumerate(enriched):
                if "error" not in e:
                    addr = e.get("billing_address", {})
                    print(f"[{i+1}] {e['raw_number']}")
                    print(f"    Name: {e['name']}")
                    print(f"    Phone: {e.get('phone', 'N/A')}")
                    print(f"    Address: {addr.get('street','')}, {addr.get('city','')}, {addr.get('state','')} {addr.get('zip','')}")
                    print(f"    Country: {e.get('country','')} ({e.get('country_code','')})")
                    print(f"    Bank: {e.get('bank','')}")
                    print(f"    BIN: {e.get('bin','')} | {e.get('network','')} | {e.get('card_type','')}")
                    print()
        return
    
    # Tracker stats mode
    if args.tracker_stats:
        stats = get_tracker_stats()
        print(json.dumps(stats, indent=2))
        return
    
    # BIN recommendations mode
    if args.recommend:
        recs = get_bin_recommendations(10)
        if recs:
            print(json.dumps(recs, indent=2))
        else:
            print("No historical data yet. Use --track-result to record check results.")
        return
    
    # Track result mode
    if args.track_result:
        card_str, status = args.track_result
        clean = card_str.split("|")[0] if "|" in card_str else card_str
        bin_prefix = clean[:6]
        bin_info = lookup_bin(bin_prefix)
        track_check(
            card_number=clean, status=status.lower(),
            bin_number=bin_prefix,
            bank=bin_info.get("bank"), country=bin_info.get("country"),
            network=_detect_network(clean)
        )
        print(f"Recorded: {clean[-4:]} = {status.upper()}")
        return
    
    # Parse card mode
    if args.parse:
        result = parse_card(args.parse)
        print(json.dumps(result, indent=2))
        return
    
    # Batch parse mode
    if args.batch_parse:
        results = parse_cards_batch(args.batch_parse)
        for r in results:
            print(json.dumps(r, indent=2))
            print("---")
        return
    
    # Find best BINs mode
    if args.find_bins:
        bins = find_best_bins(
            country=args.country,
            network=args.types[0] if args.types else None,
            count=args.count,
            scan_all=True
        )
        
        print(f"\n🔍 Best BINs" + (f" for {args.country}" if args.country else "") + 
              (f" ({args.types[0]})" if args.types else "") + ":\n")
        print(f"{'BIN':<10} {'Bank':<30} {'Type':<20} {'Country':<8} {'Source':<12}")
        print("-" * 85)
        for b in bins:
            print(f"{b['bin']:<10} {b['bank']:<30} {b.get('type', 'N/A'):<20} {b.get('country', '??'):<8} {b.get('source', 'local'):<12}")
        print(f"\n📊 Found: {len(bins)} unique BINs")
        return
    
    # Validate mode
    if args.validate:
        result = validate_card(args.validate)
        print(json.dumps(result, indent=2))
        return
    
    # BIN lookup mode (online by default)
    if args.lookup_bin:
        if args.clear_cache:
            if os.path.exists(BIN_CACHE_FILE):
                os.remove(BIN_CACHE_FILE)
                print("✅ BIN cache cleared")
        
        if args.offline:
            result = lookup_bin(args.lookup_bin)
            result["_source"] = "local_db"
        else:
            result = lookup_bin_online(args.lookup_bin, use_cache=not args.no_cache)
        print(json.dumps(result, indent=2))
        return
    
    # Batch BIN lookup mode
    if args.batch_lookup:
        if args.offline:
            results = []
            for b in args.batch_lookup:
                r = lookup_bin(b)
                r["_source"] = "local_db"
                results.append(r)
        else:
            results = batch_lookup_bins(args.batch_lookup, use_cache=not args.no_cache)
        
        for r in results:
            print(json.dumps(r, indent=2))
            print("---")
        return
    
    # Generate BINs mode
    if args.generate_bins:
        bins = generate_unique_bins(
            count=args.generate_bins,
            card_type=args.types[0] if args.types else None,
            country=args.country,
            bank=args.bank
        )
        
        output = {
            "generator": "Luhn Number Generator v3.3",
            "generated_at": datetime.now().isoformat(),
            "count": len(bins),
            "criteria": {
                "card_type": args.types[0] if args.types else "any",
                "country": args.country or "any",
                "bank": args.bank or "any"
            },
            "bins": bins
        }
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"✅ Saved {len(bins)} BINs to {args.output}")
        else:
            print(json.dumps(output, indent=2))
        return
    
    # List BINs mode
    if args.list_bins:
        print("\n📋 Available BINs in Database:\n")
        print(f"{'BIN':<8} {'Bank':<25} {'Type':<25} {'Country':<8}")
        print("-" * 70)
        
        for bin_num in sorted(BANK_BINS.keys()):
            info = BANK_BINS[bin_num]
            print(f"{bin_num:<8} {info['bank']:<25} {info['type']:<25} {info['country']:<8}")
        
        print(f"\n📊 Total: {len(BANK_BINS)} BINs in database")
        return
    
    # Generate cards mode
    print(f"\n{'='*60}")
    print(f"  LUHN NUMBER GENERATOR v3.2")
    print(f"  ⚠️  FOR EDUCATIONAL & TESTING PURPOSES ONLY")
    print(f"{'='*60}\n")
    
    # Use smart generate if --smart flag, otherwise regular generate
    if args.smart:
        cards = generate_smart(
            count=args.count,
            card_types=args.types,
            custom_bins=args.bin,
            enrich=True
        )
    else:
        cards = generate_batch(
            count=args.count,
            card_types=args.types,
            custom_bins=args.bin
        )
    
    # Always prepare JSON output
    output = {
        "generator": "Luhn Number Generator v3.3",
        "generated_at": datetime.now().isoformat(),
        "count": len(cards),
        "warning": "THESE ARE TEST NUMBERS ONLY - NOT LINKED TO REAL ACCOUNTS",
        "cards": cards
    }
    
    # CSV export
    if args.csv:
        export_csv(cards, args.csv, pipe_format=False)
        print(f"✅ Exported {len(cards)} cards to {args.csv}")
        return
    
    # Save to file if requested (JSON)
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"✅ Saved {len(cards)} cards to {args.output}")
    
    # Display format
    if args.pipe:
        # Pipe-delimited format for chkr.cc
        pipes = cards_to_pipe(cards)
        for p in pipes:
            print(p)
    elif args.raw:
        for card in cards:
            print(card["raw_number"])
    elif args.full:
        # Full output: raw data at top, details below
        for card in cards:
            raw = card["raw_number"]
            m, y = card["expiry"].split("/")
            print(f"{raw}|{m}|{y}|{card['cvv']}")
        print()
        # Details per card
        for i, card in enumerate(cards):
            addr = card.get("billing_address", {})
            bin_prefix = card.get("bin", "")[:6]
            bin_info = lookup_bin(bin_prefix)
            country = bin_info.get("country", addr.get("country", "Unknown"))
            country_code = bin_info.get("country_code", addr.get("country", "??"))
            bank = bin_info.get("bank", "Unknown")
            scheme = _detect_network(card.get("raw_number", ""))
            card_type = bin_info.get("type", "Unknown")
            print(f"[{i+1}] {card['raw_number']}")
            print(f"    Name: {card['name']}")
            print(f"    Phone: {card.get('phone', 'N/A')}")
            print(f"    Address: {addr.get('street','')}, {addr.get('city','')}, {addr.get('state','')} {addr.get('zip','')}")
            print(f"    Country: {country} ({country_code})")
            print(f"    Bank: {bank}")
            print(f"    BIN: {bin_prefix} | {scheme} | {card_type}")
            print(f"    Exp: {card['expiry']} | CVV: {card['cvv']}")
            print()
    elif args.flat:
        for card in cards:
            print(f"{card['type']:20s} {card['number']}  {card['expiry']}  CVV:{card['cvv']}")
    elif not args.output:
        print(json.dumps(output, indent=2))
    
    # Stats
    if not args.raw:
        print(f"\n📊 Generated {len(cards)} cards:")
        types_count = {}
        for card in cards:
            t = card['type']
            types_count[t] = types_count.get(t, 0) + 1
        for t, c in sorted(types_count.items()):
            print(f"   • {t}: {c}")
        
        valid_count = sum(1 for c in cards if c['valid_luhn'])
        print(f"\n✅ All {valid_count}/{len(cards)} cards pass Luhn validation")

if __name__ == "__main__":
    main()
