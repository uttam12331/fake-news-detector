import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import lookup


def test_build_lookup_params_requires_number_and_key():
    with pytest.raises(ValueError):
        lookup.build_lookup_params("", "key123")
    with pytest.raises(ValueError):
        lookup.build_lookup_params("+1234567890", "")


def test_build_lookup_params_shape():
    params = lookup.build_lookup_params(" +14155552671 ", " key123 ")
    assert params == {"access_key": "key123", "number": "+14155552671", "format": 1}


def test_normalize_lookup_response_success():
    raw = {
        "valid": True,
        "number": "14155552671",
        "international_format": "+14155552671",
        "local_format": "4155552671",
        "country_code": "US",
        "country_name": "United States of America",
        "location": "Novato",
        "carrier": "AT&T Mobility LLC",
        "line_type": "mobile",
    }
    result = lookup.normalize_lookup_response(raw)
    assert result == {
        "valid": True,
        "number": "+14155552671",
        "localFormat": "4155552671",
        "countryName": "United States of America",
        "countryCode": "US",
        "location": "Novato",
        "carrier": "AT&T Mobility LLC",
        "lineType": "mobile",
    }


def test_normalize_lookup_response_provider_error():
    raw = {"error": {"code": 101, "info": "Invalid access key"}}
    result = lookup.normalize_lookup_response(raw)
    assert result == {"valid": False, "error": "Invalid access key"}


def test_normalize_lookup_response_unexpected_shape():
    assert lookup.normalize_lookup_response(None)["valid"] is False
    assert lookup.normalize_lookup_response([1, 2, 3])["valid"] is False


def test_fetch_lookup_uses_injected_http_get():
    captured = {}

    def fake_http_get(url, params):
        captured["url"] = url
        captured["params"] = params
        return {"valid": True, "number": "447911123456", "carrier": "EE"}

    result = lookup.fetch_lookup("447911123456", "mykey", fake_http_get)
    assert captured["url"] == lookup.NUMVERIFY_BASE
    assert captured["params"]["access_key"] == "mykey"
    assert result["valid"] is True
    assert result["carrier"] == "EE"
