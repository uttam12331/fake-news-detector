"""
Builds requests to, and normalizes responses from, a Numverify-compatible
phone-number validation API. Note this is NOT a Truecaller-style identity
lookup: free/legal phone APIs return line validity, carrier, line type and
rough location — never the caller's name, which is specifically Truecaller's
own crowd-sourced (and not freely/legally replicable) data.
"""
NUMVERIFY_BASE = "http://apilayer.net/api/validate"


def build_lookup_params(number, api_key):
    number = (number or "").strip()
    api_key = (api_key or "").strip()
    if not number:
        raise ValueError("A phone number is required.")
    if not api_key:
        raise ValueError("An API key is required.")
    return {"access_key": api_key, "number": number, "format": 1}


def normalize_lookup_response(raw):
    if not isinstance(raw, dict):
        return {"valid": False, "error": "Unexpected response from the lookup provider."}
    if raw.get("error"):
        info = raw["error"].get("info") if isinstance(raw["error"], dict) else None
        return {"valid": False, "error": info or "Lookup failed."}
    return {
        "valid": bool(raw.get("valid")),
        "number": raw.get("international_format") or raw.get("number"),
        "localFormat": raw.get("local_format"),
        "countryName": raw.get("country_name"),
        "countryCode": raw.get("country_code"),
        "location": raw.get("location"),
        "carrier": raw.get("carrier"),
        "lineType": raw.get("line_type"),
    }


def fetch_lookup(number, api_key, http_get):
    """http_get(url, params) -> dict — injected so this is testable without
    making a real network call."""
    params = build_lookup_params(number, api_key)
    raw = http_get(NUMVERIFY_BASE, params)
    return normalize_lookup_response(raw)
