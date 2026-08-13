from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import Optional


class AgentStage(Enum):
    """
    Represents the high-level stage of the payment collection flow.
    """
    START = auto()
    ACCOUNT_LOOKUP = auto()
    VERIFICATION = auto()
    BALANCE_DISCLOSURE = auto()
    PAYMENT_AMOUNT = auto()
    CARD_DETAILS = auto()
    PAYMENT_PROCESSING = auto()
    COMPLETE = auto()
    TERMINATED = auto()


@dataclass
class AccountData:
    """
    Data returned by the account lookup API.

    This data is trusted account-side information and is used
    internally for verification and payment processing.
    """
    account_id: str
    full_name: str
    dob: str
    aadhaar_last4: str
    pincode: str
    balance: Decimal


@dataclass
class UserIdentityData:
    """
    Identity information supplied by the user.
    """
    full_name: Optional[str] = None
    dob: Optional[str] = None
    aadhaar_last4: Optional[str] = None
    pincode: Optional[str] = None


@dataclass
class CardData:
    """
    Card information supplied by the user.
    """
    cardholder_name: Optional[str] = None
    card_number: Optional[str] = None
    cvv: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None


@dataclass
class PaymentData:
    """
    Information needed to process a payment.
    """
    amount: Optional[Decimal] = None
    card: Optional[CardData] = None