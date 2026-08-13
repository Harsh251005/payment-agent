from decimal import Decimal

import pytest

from validators import (
    ValidationError,
    luhn_check,
    normalize_account_id,
    validate_aadhaar_last4,
    validate_amount,
    validate_card_number,
    validate_cvv,
    validate_dob,
    validate_expiry,
    validate_full_name,
    validate_pincode,
)


def test_account_id():
    assert normalize_account_id("acc 1001") == "ACC1001"


def test_name():
    assert validate_full_name("  Nithin Jain  ") == "Nithin Jain"


def test_dob():
    assert validate_dob("1988-02-29") == "1988-02-29"


def test_aadhaar():
    assert validate_aadhaar_last4("4 3 2 1") == "4321"


def test_pincode():
    assert validate_pincode("400001") == "400001"


def test_amount():
    assert validate_amount("500.00") == Decimal("500.00")


def test_card_number():
    assert (
        validate_card_number("4532 0151 1283 0366")
        == "4532015112830366"
    )


def test_luhn():
    assert luhn_check("4532015112830366") is True


def test_cvv():
    assert validate_cvv("1 2 3") == "123"


def test_expiry():
    month, year = validate_expiry(12, 2027)

    assert month == 12
    assert year == 2027


def test_invalid_account_id():
    with pytest.raises(ValidationError):
        normalize_account_id("ABC123")


def test_invalid_amount():
    with pytest.raises(ValidationError):
        validate_amount("100.123")


def test_invalid_card():
    with pytest.raises(ValidationError):
        validate_card_number("1234567890123456")


def test_invalid_cvv():
    with pytest.raises(ValidationError):
        validate_cvv("12")