import re
from datetime import date
from decimal import Decimal, InvalidOperation


class ValidationError(ValueError):
    """Raised when user-provided data fails validation."""


def normalize_account_id(account_id: str) -> str:
    """
    Normalize an account ID by removing spaces and converting it to uppercase.

    Example:
        'acc 1001' -> 'ACC1001'
    """

    normalized = re.sub(r"\s+", "", account_id).upper()

    if not re.fullmatch(r"ACC\d{4}", normalized):
        raise ValidationError("Invalid account ID format.")

    return normalized


def validate_full_name(full_name: str) -> str:
    """
    Validate that a name is non-empty.

    Exact identity matching is intentionally NOT performed here.
    That belongs to the verification layer.
    """

    normalized = " ".join(full_name.strip().split())

    if not normalized:
        raise ValidationError("Name cannot be empty.")

    return normalized


def validate_dob(dob: str) -> str:
    """
    Validate and normalize a DOB in YYYY-MM-DD format.
    """

    try:
        parsed = date.fromisoformat(dob)
    except ValueError as exc:
        raise ValidationError(
            "Date of birth must be a valid date in YYYY-MM-DD format."
        ) from exc

    return parsed.isoformat()


def validate_aadhaar_last4(aadhaar_last4: str) -> str:
    """Validate Aadhaar last four digits."""

    normalized = re.sub(r"\s+", "", aadhaar_last4)

    if not re.fullmatch(r"\d{4}", normalized):
        raise ValidationError(
            "Aadhaar last 4 must contain exactly four digits."
        )

    return normalized


def validate_pincode(pincode: str) -> str:
    """Validate a six-digit Indian pincode."""

    normalized = re.sub(r"\s+", "", pincode)

    if not re.fullmatch(r"\d{6}", normalized):
        raise ValidationError(
            "Pincode must contain exactly six digits."
        )

    return normalized


def validate_amount(amount: str) -> Decimal:
    """
    Validate payment amount.

    Requirements from the assignment:
    - Must be greater than zero.
    - Must have no more than two decimal places.
    """

    try:
        value = Decimal(amount)
    except InvalidOperation as exc:
        raise ValidationError("Invalid payment amount.") from exc

    if value <= 0:
        raise ValidationError("Payment amount must be greater than zero.")

    if value.as_tuple().exponent < -2:
        raise ValidationError(
            "Payment amount cannot have more than two decimal places."
        )

    return value


def validate_card_number(card_number: str) -> str:
    """
    Validate card number format and Luhn checksum.
    """

    normalized = re.sub(r"[\s-]+", "", card_number)

    if not normalized.isdigit():
        raise ValidationError("Card number must contain digits only.")

    if not 13 <= len(normalized) <= 19:
        raise ValidationError("Invalid card number length.")

    if not luhn_check(normalized):
        raise ValidationError("Invalid card number.")

    return normalized


def luhn_check(card_number: str) -> bool:
    """Validate a card number using the Luhn algorithm."""

    total = 0
    digits = list(map(int, card_number))

    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2

            if digit > 9:
                digit -= 9

        total += digit

    return total % 10 == 0


def validate_cvv(cvv: str) -> str:
    """
    Validate CVV length.

    Standard cards use 3 digits; Amex uses 4.
    """

    normalized = re.sub(r"\s+", "", cvv)

    if not re.fullmatch(r"\d{3,4}", normalized):
        raise ValidationError("CVV must contain 3 or 4 digits.")

    return normalized


def validate_expiry(expiry_month: int, expiry_year: int) -> tuple[int, int]:
    """
    Validate expiry month/year and ensure the card has not expired.
    """

    if not 1 <= expiry_month <= 12:
        raise ValidationError("Expiry month must be between 1 and 12.")

    if expiry_year < 100:
        raise ValidationError("Expiry year must contain four digits.")

    today = date.today()

    if (
            expiry_year < today.year
            or (
            expiry_year == today.year
            and expiry_month < today.month
    )
    ):
        raise ValidationError("Card has expired.")

    return expiry_month, expiry_year


def verify_identity(
    user_name: str | None,
    user_dob: str | None,
    user_aadhaar_last4: str | None,
    user_pincode: str | None,
    account_name: str,
    account_dob: str,
    account_aadhaar_last4: str,
    account_pincode: str,
) -> bool:
    """
    Verify the user's identity using the assignment's strict rules.

    Requirements:
    - Full name must match exactly.
    - At least one secondary factor must also match:
      DOB OR Aadhaar last 4 OR pincode.
    """

    if user_name is None:
        return False

    # Name comparison is intentionally strict and case-sensitive.
    name_matches = user_name == account_name

    if not name_matches:
        return False

    secondary_match = (
        (user_dob is not None and user_dob == account_dob)
        or
        (
            user_aadhaar_last4 is not None
            and user_aadhaar_last4 == account_aadhaar_last4
        )
        or
        (
            user_pincode is not None
            and user_pincode == account_pincode
        )
    )

    return secondary_match