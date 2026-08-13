from models import CardData
from parser import InputParser
from state import ConversationState
from tools import PaymentAPI, PaymentAPIError
from validators import (
    ValidationError,
    normalize_account_id,
    verify_identity,
)


class Agent:
    """
    Conversational payment collection agent.

    The Agent owns the conversation state and orchestrates:
    - natural-language extraction
    - input validation
    - account lookup
    - state transitions
    """

    def __init__(
        self,
        parser: InputParser | None = None,
        api: PaymentAPI | None = None,
    ):
        self.state = ConversationState()

        self.parser = parser or InputParser()
        self.api = api or PaymentAPI()

    def next(self, user_input: str) -> dict:
        """
        Process exactly one user turn.

        The same Agent instance must be reused across turns so that
        conversation state is preserved.
        """

        if not isinstance(user_input, str):
            raise TypeError("user_input must be a string.")

        user_input = user_input.strip()

        if not user_input:
            return {
                "message": "I didn't receive any information. "
                           "Please tell me your account ID."
            }

        extraction = self.parser.extract(user_input)

        self._merge_extraction(extraction)

        return self._handle_current_stage()

    def _merge_extraction(self, extraction):
        """
        Merge newly extracted information into the conversation state.
        """

        if extraction.account_id:
            try:
                self.state.account_id = normalize_account_id(
                    extraction.account_id
                )
            except ValidationError:
                self.state.last_error = "invalid_account_id"

        if extraction.full_name:
            self.state.identity.full_name = extraction.full_name

        if extraction.dob:
            self.state.identity.dob = extraction.dob

        if extraction.aadhaar_last4:
            self.state.identity.aadhaar_last4 = extraction.aadhaar_last4

        if extraction.pincode:
            self.state.identity.pincode = extraction.pincode

        if extraction.amount:
            self.state.payment.amount = extraction.amount

        if extraction.cardholder_name:
            self.state.payment.card = self.state.payment.card or CardData()

            self.state.payment.card.cardholder_name = (
                extraction.cardholder_name
            )

        if extraction.card_number:
            self.state.payment.card = self.state.payment.card or CardData()

            self.state.payment.card.card_number = (
                extraction.card_number
            )

        if extraction.cvv:
            self.state.payment.card = self.state.payment.card or CardData()

            self.state.payment.card.cvv = extraction.cvv

        if extraction.expiry_month:
            self.state.payment.card = self.state.payment.card or CardData()

            self.state.payment.card.expiry_month = (
                extraction.expiry_month
            )

        if extraction.expiry_year:
            self.state.payment.card = self.state.payment.card or CardData()

            self.state.payment.card.expiry_year = (
                extraction.expiry_year
            )

    def _handle_current_stage(self) -> dict:

        from models import AgentStage

        if self.state.stage == AgentStage.START:
            self.state.stage = AgentStage.ACCOUNT_LOOKUP

        if self.state.stage == AgentStage.ACCOUNT_LOOKUP:
            return self._handle_account_lookup()

        if self.state.stage == AgentStage.VERIFICATION:
            return self._handle_verification()

        if self.state.stage == AgentStage.BALANCE_DISCLOSURE:
            return {
                "message": "How much would you like to pay?"
            }

        return {
            "message": "I'm sorry, but I couldn't determine the next step."
        }

    def _handle_account_lookup(self) -> dict:
        """
        Look up the account once a valid account ID is available.
        """

        if self.state.last_error == "invalid_account_id":
            self.state.last_error = None

            return {
                "message": (
                    "That doesn't look like a valid account ID. "
                    "Please provide an account ID such as ACC1001."
                )
            }

        if not self.state.account_id:
            return {
                "message": (
                    "Hello! Please share your account ID "
                    "to get started."
                )
            }

        try:
            account_response = self.api.lookup_account(
                self.state.account_id
            )

        except PaymentAPIError as exc:
            if str(exc) == "account_not_found":
                self.state.account_id = None

                return {
                    "message": (
                        "I couldn't find an account with that ID. "
                        "Please check it and provide your account ID again."
                    )
                }

            return {
                "message": (
                    "I'm unable to access the account service right now. "
                    "Please try again shortly."
                )
            }

        self.state.account = self._build_account_data(account_response)

        self.state.stage = self.state.stage.VERIFICATION

        return {
            "message": (
                "Got it. Could you please confirm your full name?"
            )
        }

    @staticmethod
    def _build_account_data(data):
        """
        Convert the raw API response into our internal AccountData model.
        """

        from decimal import Decimal
        from models import AccountData

        return AccountData(
            account_id=data["account_id"],
            full_name=data["full_name"],
            dob=data["dob"],
            aadhaar_last4=data["aadhaar_last4"],
            pincode=data["pincode"],
            balance=Decimal(str(data["balance"])),
        )

    def _handle_verification(self) -> dict:
        """
        Verify the user's identity against the account data.
        """

        if self.state.account is None:
            return {
                "message": (
                    "I need to look up your account before "
                    "I can verify your identity."
                )
            }

        identity = self.state.identity
        account = self.state.account

        # We need the user's full name first.
        if identity.full_name is None:
            return {
                "message": (
                    "Please provide your full name."
                )
            }

        # We need at least one secondary verification factor.
        has_secondary_factor = any(
            value is not None
            for value in (
                identity.dob,
                identity.aadhaar_last4,
                identity.pincode,
            )
        )

        if not has_secondary_factor:
            return {
                "message": (
                    "Thanks. Please provide your date of birth, "
                    "Aadhaar last 4 digits, or pincode."
                )
            }

        try:
            verified = verify_identity(
                user_name=identity.full_name,
                user_dob=identity.dob,
                user_aadhaar_last4=identity.aadhaar_last4,
                user_pincode=identity.pincode,
                account_name=account.full_name,
                account_dob=account.dob,
                account_aadhaar_last4=account.aadhaar_last4,
                account_pincode=account.pincode,
            )
        except Exception:
            return {
                "message": (
                    "I couldn't complete identity verification. "
                    "Please try again."
                )
            }

        if verified:
            self.state.verified = True

            from models import AgentStage

            self.state.stage = AgentStage.BALANCE_DISCLOSURE

            return {
                "message": (
                    f"Identity verified. Your outstanding balance is "
                    f"₹{account.balance:.2f}."
                )
            }

        self.state.verification_attempts += 1

        remaining_attempts = 3 - self.state.verification_attempts

        if self.state.verification_attempts >= 3:
            from models import AgentStage

            self.state.stage = AgentStage.TERMINATED

            return {
                "message": (
                    "I'm sorry, but I couldn't verify your identity "
                    "after multiple attempts. For your security, "
                    "we can't continue with the payment."
                )
            }

        return {
            "message": (
                    "I couldn't verify those details. "
                    "Please check your information and try again."
                    + (
                        f" You have {remaining_attempts} attempt(s) remaining."
                        if remaining_attempts > 0
                        else ""
                    )
            )
        }