from dataclasses import dataclass
from enum import Enum, auto
import json
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from models import CardData, AgentStage
from parser import InputParser
from state import ConversationState
from tools import PaymentAPI, PaymentAPIError
from settings import settings
from prompts import get_generation_prompt
from validators import (
    ValidationError,
    normalize_account_id,
    validate_amount,
    validate_aadhaar_last4,
    validate_card_number,
    validate_cvv,
    validate_dob,
    validate_expiry,
    validate_pincode,
    validate_full_name,
    verify_identity,
)


class OutcomeType(Enum):
    CONTINUE = auto()
    RESPOND = auto()


@dataclass(frozen=True)
class AgentOutcome:
    outcome: OutcomeType
    reason: str = ""


class Agent:
    def __init__(
            self,
            parser: InputParser | None = None,
            api: PaymentAPI | None = None,
            llm_client: OpenAI | None = None,
    ):
        self.state = ConversationState()
        self.parser = parser or InputParser()
        self.api = api or PaymentAPI()

        # LLM is optional — agent must be fully functional without it.
        if llm_client is not None:
            self.llm = llm_client
        else:
            api_key = settings.OPENAI_API_KEY
            self.llm = OpenAI(api_key=api_key) if api_key else None

        self._turn_errors: set[str] = set()
        self._turn_flags: set[str] = set()
        self._last_user_input: str = ""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def next(self, user_input: str) -> dict:
        if not isinstance(user_input, str):
            raise TypeError("user_input must be a string.")

        user_input = user_input.strip()
        self._last_user_input = user_input

        if not user_input:
            return {
                "message": "I didn't receive any information. Please tell me your account ID."
            }

        self.state.last_error = None
        self._turn_errors.clear()
        self._turn_flags.clear()

        # 1. LLM Extraction (Structured Outputs) happens here via your parser
        safe_state_dict = self._get_safe_state()
        safe_state_json = json.dumps(safe_state_dict, indent=2)

        balance_context = str(self.state.account.balance) if self.state.account else None

        # 2. Pass the state to the parser so it can resolve coreferences
        extraction = self.parser.extract(
            user_input,
            current_stage=self.state.stage.name,
            balance_context=balance_context,
            safe_state_json=safe_state_json
        )

        # 2. Deterministic Validation & State Merge
        self._merge_extraction(extraction)

        # 3. Deterministic State Machine Transitions
        max_transitions = 12
        for _ in range(max_transitions):
            result = self._handle_current_stage()

            if result.outcome == OutcomeType.RESPOND:
                return {
                    "message": self._build_response(result.reason)
                }

        return {
            "message": "Agent exceeded the maximum number of workflow transitions."
        }

    # ------------------------------------------------------------------
    # Extraction -> State (Unchanged - Great out-of-order handling)
    # ------------------------------------------------------------------

    def _merge_extraction(self, extraction) -> None:
        if extraction.account_id:
            if self.state.account is None:
                try:
                    self.state.account_id = normalize_account_id(extraction.account_id)
                except ValidationError:
                    self.state.last_error = "invalid_account_id"
                    self._turn_errors.add("invalid_account_id")

        if extraction.full_name:
            try:
                self.state.identity.full_name = validate_full_name(extraction.full_name)
            except ValidationError:
                self.state.last_error = "invalid_name"
                self._turn_errors.add("invalid_name")

        if extraction.dob:
            try:
                self.state.identity.dob = validate_dob(extraction.dob)
            except ValidationError:
                self.state.last_error = "invalid_dob"
                self._turn_errors.add("invalid_dob")

        if extraction.aadhaar_last4:
            try:
                self.state.identity.aadhaar_last4 = validate_aadhaar_last4(extraction.aadhaar_last4)
            except ValidationError:
                self.state.last_error = "invalid_aadhaar"
                self._turn_errors.add("invalid_aadhaar")

        if extraction.pincode:
            try:
                self.state.identity.pincode = validate_pincode(extraction.pincode)
            except ValidationError:
                self.state.last_error = "invalid_pincode"
                self._turn_errors.add("invalid_pincode")

        if extraction.amount:
            try:
                self.state.payment.amount = validate_amount(extraction.amount)
            except ValidationError:
                self.state.last_error = "invalid_amount"
                self._turn_errors.add("invalid_amount")

        if extraction.cardholder_name:
            try:
                card = self.state.payment.card or CardData()
                card.cardholder_name = validate_full_name(extraction.cardholder_name)
                self.state.payment.card = card
            except ValidationError:
                self.state.last_error = "invalid_cardholder_name"
                self._turn_errors.add("invalid_cardholder_name")

        if extraction.card_number:
            try:
                card = self.state.payment.card or CardData()
                card.card_number = validate_card_number(extraction.card_number)
                self.state.payment.card = card
            except ValidationError:
                self.state.last_error = "invalid_card_number"
                self._turn_errors.add("invalid_card_number")

        if extraction.cvv:
            try:
                card = self.state.payment.card or CardData()
                card.cvv = validate_cvv(extraction.cvv)
                self.state.payment.card = card
            except ValidationError:
                self.state.last_error = "invalid_cvv"
                self._turn_errors.add("invalid_cvv")

        if extraction.expiry_month is not None or extraction.expiry_year is not None:
            if extraction.expiry_month is None or extraction.expiry_year is None:
                self.state.last_error = "invalid_expiry"
                self._turn_errors.add("invalid_expiry")
            else:
                try:
                    card = self.state.payment.card or CardData()
                    month, year = validate_expiry(extraction.expiry_month, extraction.expiry_year)
                    card.expiry_month = month
                    card.expiry_year = year
                    self.state.payment.card = card
                except ValidationError:
                    self.state.last_error = "invalid_expiry"
                    self._turn_errors.add("invalid_expiry")

    # ------------------------------------------------------------------
    # Workflow controller (Unchanged - Keeps strict API/Business rules)
    # ------------------------------------------------------------------

    def _handle_current_stage(self) -> AgentOutcome:
        if self.state.stage == AgentStage.START:
            self.state.stage = AgentStage.ACCOUNT_LOOKUP

        if self.state.stage == AgentStage.ACCOUNT_LOOKUP:
            return self._handle_account_lookup()

        if self.state.stage == AgentStage.VERIFICATION:
            return self._handle_verification()

        if self.state.stage == AgentStage.BALANCE_DISCLOSURE:
            return self._handle_balance_disclosure()

        if self.state.stage == AgentStage.PAYMENT_AMOUNT:
            return self._handle_payment_amount()

        if self.state.stage == AgentStage.CARD_DETAILS:
            return self._handle_card_details()

        if self.state.stage == AgentStage.PAYMENT_PROCESSING:
            return self._handle_payment_processing()

        if self.state.stage == AgentStage.COMPLETE:
            return self._respond("already_complete")

        if self.state.stage == AgentStage.TERMINATED:
            return self._respond("terminated")

        return self._respond("unknown_state")

    # ------------------------------------------------------------------
    # Handlers (Unchanged - Strictly deterministic logic is best here)
    # ------------------------------------------------------------------

    def _handle_account_lookup(self) -> AgentOutcome:
        if "invalid_account_id" in self._turn_errors:
            return self._respond("invalid_account_id")
        if not self.state.account_id:
            return self._respond("need_account_id")

        try:
            account_response = self.api.lookup_account(self.state.account_id)
        except PaymentAPIError as exc:
            if str(exc) == "account_not_found":
                self.state.account_id = None
                return self._respond("account_not_found")
            return self._respond("account_service_unavailable")

        self.state.account = self._build_account_data(account_response)
        self.state.stage = AgentStage.VERIFICATION
        self._turn_flags.add("account_found")
        return self._continue()

    @staticmethod
    def _build_account_data(data):
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

    def _handle_verification(self) -> AgentOutcome:
        if self.state.account is None:
            return self._respond("verification_without_account")

        identity_errors = {"invalid_name", "invalid_dob", "invalid_aadhaar", "invalid_pincode"}
        if self._turn_errors & identity_errors:
            return self._respond("invalid_identity_input")

        identity = self.state.identity
        account = self.state.account

        if identity.full_name is None:
            return self._respond("need_full_name")

        has_secondary_factor = any(
            value is not None for value in (identity.dob, identity.aadhaar_last4, identity.pincode)
        )

        if not has_secondary_factor:
            return self._respond("need_secondary_factor")

        try:
            is_verified, failure_reason = verify_identity(
                identity,
                account
            )
        except Exception:
            return self._respond("verification_error")

        if is_verified:
            self.state.verified = True
            self.state.stage = AgentStage.BALANCE_DISCLOSURE
            self._turn_flags.add("verified")
            return self._continue()

        self.state.verification_reattempts += 1
        if self.state.verification_reattempts >= 3:
            self.state.stage = AgentStage.TERMINATED
            return self._respond("verification_terminated")

        if failure_reason == "name_mismatch":
            return self._respond("verification_name_mismatch")

        return self._respond("verification_failed")

    def _handle_balance_disclosure(self) -> AgentOutcome:
        if not self.state.verified or self.state.account is None:
            self.state.stage = AgentStage.TERMINATED
            return self._respond("unverified_state")
        self.state.stage = AgentStage.PAYMENT_AMOUNT
        return self._continue()

    def _handle_payment_amount(self) -> AgentOutcome:
        if "invalid_amount" in self._turn_errors:
            return self._respond("invalid_amount")
        if self.state.payment.amount is None:
            return self._respond("need_payment_amount")
        if self.state.account is None:
            self.state.stage = AgentStage.TERMINATED
            return self._respond("missing_account_for_payment")

        if self.state.payment.amount > self.state.account.balance:
            self.state.payment.amount = None
            return self._respond("amount_exceeds_balance")

        self.state.stage = AgentStage.CARD_DETAILS
        return self._continue()

    def _handle_card_details(self) -> AgentOutcome:
        card_errors = {"invalid_cardholder_name", "invalid_card_number", "invalid_cvv", "invalid_expiry"}
        if self._turn_errors & card_errors:
            return self._respond("invalid_card_details")

        card = self.state.payment.card
        if card is None:
            return self._respond("need_card_details")

        missing_fields = []
        if not card.cardholder_name: missing_fields.append("cardholder name")
        if not card.card_number: missing_fields.append("card number")
        if not card.cvv: missing_fields.append("CVV")
        if card.expiry_month is None: missing_fields.append("expiry month")
        if card.expiry_year is None: missing_fields.append("expiry year")

        if missing_fields:
            return self._respond("missing_card_fields")

        self.state.stage = AgentStage.PAYMENT_PROCESSING
        return self._continue()

    def _handle_payment_processing(self) -> AgentOutcome:
        if not self.state.verified:
            self.state.stage = AgentStage.TERMINATED
            return self._respond("payment_without_verification")
        if self.state.account is None:
            self.state.stage = AgentStage.TERMINATED
            return self._respond("payment_without_account")
        if self.state.payment.amount is None:
            self.state.stage = AgentStage.PAYMENT_AMOUNT
            return self._respond("need_payment_amount")

        card = self.state.payment.card
        if card is None:
            self.state.stage = AgentStage.CARD_DETAILS
            return self._respond("need_card_details")

        expiry_month = card.expiry_month
        expiry_year = card.expiry_year
        if expiry_month is None or expiry_year is None:
            self.state.stage = AgentStage.CARD_DETAILS
            return self._respond("payment_invalid_expiry")

        try:
            result = self.api.process_payment(
                account_id=self.state.account.account_id,
                amount=self.state.payment.amount,
                cardholder_name=card.cardholder_name,
                card_number=card.card_number,
                cvv=card.cvv,
                expiry_month=expiry_month,
                expiry_year=expiry_year
            )
        except PaymentAPIError as exc:
            error_code = str(exc)
            if error_code == "insufficient_balance":
                self.state.stage = AgentStage.PAYMENT_AMOUNT
                self.state.payment.amount = None
                return self._respond("payment_insufficient_balance")
            if error_code == "invalid_card":
                self.state.stage = AgentStage.CARD_DETAILS
                self._clear_card_field("card_number")
                return self._respond("payment_invalid_card")
            if error_code == "invalid_cvv":
                self.state.stage = AgentStage.CARD_DETAILS
                self._clear_card_field("cvv")
                return self._respond("payment_invalid_cvv")
            if error_code == "invalid_expiry":
                self.state.stage = AgentStage.CARD_DETAILS
                self._clear_card_field("expiry_month", "expiry_year")
                return self._respond("payment_invalid_expiry")
            if error_code == "invalid_amount":
                self.state.stage = AgentStage.PAYMENT_AMOUNT
                self.state.payment.amount = None
                return self._respond("payment_invalid_amount")

            self.state.stage = AgentStage.TERMINATED
            self._clear_card_data()
            return self._respond("payment_service_failure")

        transaction_id = result.get("transaction_id")
        if not result.get("success") or not transaction_id:
            self.state.stage = AgentStage.TERMINATED
            self._clear_card_data()
            return self._respond("payment_failed")

        self.state.transaction_id = transaction_id
        self.state.stage = AgentStage.COMPLETE
        self._clear_card_data()
        return self._respond("payment_success")

    # ------------------------------------------------------------------
    # Dynamic NLG Response System (Hybrid Approach)
    # ------------------------------------------------------------------

    def _build_response(self, reason: str) -> str:

        reason_hints = {
            "need_secondary_factor": "Explicitly ask the user to provide either their Date of Birth, PIN code, or the last 4 digits of their Aadhaar.",
            "verification_name_mismatch": "Inform the user that the name provided does not match the account records, and ask them to confirm their full registered name.",
            "verification_failed": "Inform the user that the verification details did not match our records, and ask them to verify their Date of Birth, PIN code, or last 4 digits of Aadhaar.",
            "verification_lockout": "Inform the user that verification attempts have been exhausted and the session is terminated.",
            "missing_card_fields": "Look at the 'missing_card_fields' in the JSON state and explicitly list exactly WHICH card fields they still need to provide.",
            "need_card_details": "Explicitly ask the user for their Card Number, CVV, Expiry Date, and Cardholder Name.",
            "invalid_identity_input": "Look at the Validation Errors and explicitly state which identity input was incorrect, then ask them to try again.",
            "payment_insufficient_balance": f"Inform the user their amount exceeds the balance and ask for a smaller amount. Current balance: {self.state.account.balance if self.state.account else "Unknown"}"
        }
        hint = reason_hints.get(reason, "Communicate the system action clearly and gently guide the user to the next step.")

        # 2. Construct the highly-contextual prompt
        system_prompt = get_generation_prompt(
            reason=reason,
            reason_hint=hint,
            errors=", ".join(self._turn_errors) if self._turn_errors else "None",
            last_user_input=self._last_user_input,
            safe_state_json=json.dumps(self._get_safe_state(), indent=2),
            balance_str=f"₹{self.state.account.balance:.2f}" if (self.state.verified and self.state.account) else "Unknown",
            retries_left=3 - self.state.verification_reattempts,
            txn_id=self.state.transaction_id or "None"
        )

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the next response."}
        ]

        try:
            response = self.llm.chat.completions.create(
                model=settings.GENERATION_MODEL,
                messages=messages,
                temperature=0,
                max_completion_tokens=150,
                stream=False
            )

            # Safely handle the possibility of content being None
            content = response.choices[0].message.content
            return content.strip() if content else self._fallback_response(reason)

        except Exception as ex:
            # 3. Production-Ready Deterministic Fallback
            # If the LLM goes down or times out, the agent gracefully degrades
            # to a safe, generic deterministic response instead of crashing.
            print(f"[LLM generation failed, using fallback] {type(ex).__name__}: {ex}\n")
            return self._fallback_response(reason)

    def _fallback_response(self, reason: str) -> str:
        fallback_map = {
            "need_account_id": "Please provide your account ID to get started.",
            "invalid_account_id": "That account ID doesn't look valid. Please check and try again.",
            "account_not_found": "We couldn't find an account with that ID. Please double-check and try again.",
            "account_service_unavailable": "Our account lookup service is temporarily unavailable. Please try again shortly.",
            "verification_without_account": "Something went wrong — no account is on file yet. Please provide your account ID.",
            "need_full_name": "Please provide your full name for verification.",
            "need_secondary_factor": "Please provide your date of birth, pincode, or the last 4 digits of your Aadhaar.",
            "invalid_identity_input": "Some of the identity details you provided look invalid. Please try again.",
            "verification_error": "We ran into an issue verifying your identity. Please try again.",
            "verification_failed": f"We couldn't verify your identity with those details. You have {3 - self.state.verification_reattempts} attempt(s) left.",
            "verification_terminated": "Identity verification failed too many times. This session has been ended for security reasons.",
            "unverified_state": "Something went wrong — your identity isn't verified. This session has been ended.",
            "need_payment_amount": "How much would you like to pay?",
            "invalid_amount": "That amount doesn't look valid. Please enter a valid payment amount.",
            "missing_account_for_payment": "Something went wrong — no account is on file for this payment. This session has been ended.",
            "amount_exceeds_balance": (
                f"That amount exceeds your outstanding balance of ₹{self.state.account.balance:.2f}. Please enter a smaller amount."
                if self.state.account else
                "That amount exceeds your outstanding balance. Please enter a smaller amount."
            ),
            "need_card_details": "Please provide your card number, CVV, expiry date, and cardholder name.",
            "invalid_card_details": "Some of the card details you provided look invalid. Please try again.",
            "missing_card_fields": "Some card details are still missing. Please provide the remaining fields (card number, CVV, expiry date, and cardholder name).",
            "payment_without_verification": "Something went wrong — payment can't proceed without verification. This session has been ended.",
            "payment_without_account": "Something went wrong — no account is on file for this payment. This session has been ended.",
            "payment_invalid_expiry": "The card expiry date appears invalid. Please provide it again.",
            "payment_insufficient_balance": "The payment couldn't go through due to insufficient balance. Please enter a smaller amount.",
            "payment_invalid_card": "That card number was declined as invalid. Please provide your card number again.",
            "payment_invalid_cvv": "That CVV was declined as invalid. Please provide your CVV again.",
            "payment_invalid_amount": "That payment amount was declined as invalid. Please enter the amount again.",
            "payment_service_failure": "We couldn't process your payment due to a service issue. Please try again later.",
            "payment_failed": "Your payment could not be completed. Please try again later.",
            "payment_success": f"Payment successful! Thank you. Transaction ID: {self.state.transaction_id}",
            "already_complete": "This transaction is already complete. Thank you!",
            "terminated": "This session has ended. Please start a new conversation to make a payment.",
            "unknown_state": "Something unexpected happened. Please start a new conversation.",
        }
        return fallback_map.get(reason, "I need some more information to proceed. Please follow the prompt.")


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _continue() -> AgentOutcome:
        return AgentOutcome(outcome=OutcomeType.CONTINUE)

    @staticmethod
    def _respond(reason: str) -> AgentOutcome:
        return AgentOutcome(outcome=OutcomeType.RESPOND, reason=reason)

    def _clear_card_data(self) -> None:
        self.state.payment.card = None

    def _clear_card_field(self, *fields: str) -> None:
        card = self.state.payment.card
        if card is None: return
        for field in fields:
            setattr(card, field, None)

    def _get_safe_state(self) -> dict:
        """
        Creates a sanitized snapshot of the current state for the LLM.
        Masks all sensitive identity and payment data as per security requirements.
        """
        safe_state: dict[str, Any] = {
            "current_stage": self.state.stage.name,
            "verification_reattempts": self.state.verification_reattempts,
            "is_verified": self.state.verified,
            "last_error": self.state.last_error,
            "transaction_id": self.state.transaction_id,
        }

        # Safe Account Data (Excluding real DOB/Aadhaar/Pincode)
        if self.state.account:
            safe_state["account"] = {
                "balance_due": float(self.state.account.balance),
                "account_name": self.state.account.full_name
            }
        else:
            safe_state["account"] = None

        # Masked Identity Data
        safe_state["identity_collected"] = {
            "name": self.state.identity.full_name,  # Safe to pass for coreference
            "has_dob": bool(self.state.identity.dob),
            "has_aadhaar": bool(self.state.identity.aadhaar_last4),
            "has_pincode": bool(self.state.identity.pincode),
        }

        # Masked Payment Data
        safe_state["payment"] = {
            "amount": float(self.state.payment.amount) if self.state.payment.amount else None,
            "has_card_data": False
        }

        if self.state.payment.card:
            safe_state["payment"]["has_card_data"] = True
            safe_state["payment"]["missing_card_fields"] = []

            # Help the LLM know EXACTLY what is missing
            if not self.state.payment.card.card_number:
                safe_state["payment"]["missing_card_fields"].append("card_number")
            if not self.state.payment.card.cvv:
                safe_state["payment"]["missing_card_fields"].append("cvv")
            if self.state.payment.card.expiry_month is None:
                safe_state["payment"]["missing_card_fields"].append("expiry_date")
            if not self.state.payment.card.cardholder_name:
                safe_state["payment"]["missing_card_fields"].append("cardholder_name")

        return safe_state