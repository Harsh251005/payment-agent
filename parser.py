from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv()


class ExtractionResult(BaseModel):
    """
    Structured information extracted from a single user message.
    """

    account_id: Optional[str] = Field(
        default=None,
        description="Account ID mentioned by the user, such as ACC1001."
    )

    full_name: Optional[str] = Field(
        default=None,
        description="The user's full name exactly as stated."
    )

    dob: Optional[str] = Field(
        default=None,
        description="Date of birth normalized to YYYY-MM-DD when unambiguous."
    )

    aadhaar_last4: Optional[str] = Field(
        default=None,
        description="Last four digits of Aadhaar."
    )

    pincode: Optional[str] = Field(
        default=None,
        description="User's six-digit pincode."
    )

    amount: Optional[str] = Field(
        default=None,
        description="Payment amount as a decimal string, for example '500.00'."
    )

    cardholder_name: Optional[str] = Field(
        default=None,
        description="Cardholder name exactly as stated by the user."
    )

    card_number: Optional[str] = Field(
        default=None,
        description="Full card number as digits only."
    )

    cvv: Optional[str] = Field(
        default=None,
        description="Card CVV as digits only."
    )

    expiry_month: Optional[int] = Field(
        default=None,
        description="Card expiry month as an integer from 1 to 12."
    )

    expiry_year: Optional[int] = Field(
        default=None,
        description="Card expiry year as a four-digit year."
    )


class InputParser:
    """
    Converts natural-language user messages into structured data.

    This class performs semantic extraction only.
    It does not perform verification or business-rule decisions.
    """

    def __init__(
        self,
        client: OpenAI | None = None,
        model: str = "gpt-5-mini",
    ):
        self.client = client or OpenAI()
        self.model = model

    def extract(self, user_input: str) -> ExtractionResult:
        """
        Extract structured fields from one user message.
        """

        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You extract structured information from a user's "
                        "payment-collection message.\n\n"

                        "Rules:\n"
                        "1. Extract only information explicitly stated or "
                        "clearly implied by the user.\n"
                        "2. Leave fields as null when the information is "
                        "missing or ambiguous.\n"
                        "3. A single message may contain multiple fields.\n"
                        "4. Preserve names exactly as stated by the user.\n"
                        "5. Normalize dates to YYYY-MM-DD when unambiguous.\n"
                        "6. Normalize card numbers and CVV to digits only.\n"
                        "7. Normalize spoken numbers such as 'one two three' "
                        "to '123'.\n"
                        "8. Convert payment amounts such as 'a thousand "
                        "rupees' to a decimal string such as '1000.00'.\n"
                        "9. Convert expiry expressions such as 'December "
                        "2027' or '12/27' into expiry_month and expiry_year.\n"
                        "10. Do not invent, guess, or infer missing values."
                    ),
                },
                {
                    "role": "user",
                    "content": user_input,
                },
            ],
            text_format=ExtractionResult,
        )

        if response.output_parsed is None:
            raise RuntimeError("The model did not return structured output.")

        return response.output_parsed