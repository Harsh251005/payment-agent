import os
from decimal import Decimal
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class PaymentAPIError(Exception):
    """Raised when the payment verification API returns an error."""


class PaymentAPI:
    """
    Thin wrapper around the Prodigal payment verification API.

    This class is responsible only for HTTP communication.
    Business logic and conversation flow stay in Agent.
    """

    def __init__(self, base_url: str | None = None, timeout: int = 10):
        self.base_url = (
                base_url
                or os.getenv(
            "API_BASE_URL",
            "https://se-payment-verification-api.service.external.usea2.aws.prodigaltech.com",
        )
        ).rstrip("/")

        self.timeout = timeout

    def lookup_account(self, account_id: str) -> dict[str, Any]:
        """Look up an account by account ID."""

        url = f"{self.base_url}/api/lookup-account"

        payload = {
            "account_id": account_id
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PaymentAPIError(
                "Unable to reach the account lookup service."
            ) from exc

        if response.status_code == 404:
            raise PaymentAPIError(
                "account_not_found"
            )

        if not response.ok:
            raise PaymentAPIError(
                f"Account lookup failed with HTTP {response.status_code}."
            )

        try:
            return response.json()
        except ValueError as exc:
            raise PaymentAPIError(
                "Account lookup returned an invalid response."
            ) from exc

    def process_payment(
            self,
            account_id: str,
            amount: Decimal,
            cardholder_name: str,
            card_number: str,
            cvv: str,
            expiry_month: int,
            expiry_year: int,
    ) -> dict[str, Any]:
        """Process a card payment against the account balance."""

        url = f"{self.base_url}/api/process-payment"

        payload = {
            "account_id": account_id,
            "amount": float(amount),
            "payment_method": {
                "type": "card",
                "card": {
                    "cardholder_name": cardholder_name,
                    "card_number": card_number,
                    "cvv": cvv,
                    "expiry_month": expiry_month,
                    "expiry_year": expiry_year,
                },
            },
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PaymentAPIError(
                "Unable to reach the payment service."
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise PaymentAPIError(
                "Payment service returned an invalid response."
            ) from exc

        if response.status_code == 422:
            error_code = data.get("error_code", "unknown_error")
            raise PaymentAPIError(error_code)

        if not response.ok:
            raise PaymentAPIError(
                f"Payment failed with HTTP {response.status_code}."
            )

        return data