from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field
from prompts import get_extraction_prompt
from dotenv import load_dotenv

load_dotenv()


class ExtractionResult(BaseModel):
    """
    Structured information extracted from a single user message.
    """

    account_id: Optional[str] = Field(
        default=None,
        description="The alphanumeric account ID (e.g., 'ACC1001'). Extract even if embedded in conversational text."
    )

    full_name: Optional[str] = Field(
        default=None,
        description=(
            "The user's full name. Extract any general mention of the user's name here."
        )
    )

    dob: Optional[str] = Field(
        default=None,
        description="Date of birth. You MUST convert any provided date format into strictly YYYY-MM-DD (e.g., 'May 14 1990' becomes '1990-05-14')."
    )

    aadhaar_last4: Optional[str] = Field(
        default=None,
        description="Strictly the last four digits of the user's Aadhaar number. Strip any spaces or text."
    )

    pincode: Optional[str] = Field(
        default=None,
        description="The six-digit postal pincode. Strip any spaces (e.g., '4 0 0 0 0 1' becomes '400001')."
    )

    amount: Optional[str] = Field(
        default=None,
        description="The intended payment amount converted to a standard decimal string (e.g., 'a thousand rupees' becomes '1000.00', '500' becomes '500.00')."
    )

    cardholder_name: Optional[str] = Field(
        default=None,
        description=(
            "The name printed on the credit card. ONLY extract a name here if the user "
            "explicitly specifies it is for the card (e.g., 'the name on the card is Nithin'). "
            "Otherwise, put names in 'full_name'."
        )
    )

    card_number: Optional[str] = Field(
        default=None,
        description="The full credit card number. You MUST extract this as a single string of digits only, stripping all spaces and dashes."
    )

    cvv: Optional[str] = Field(
        default=None,
        description="The 3 or 4-digit CVV security code as digits only. Convert spoken words like 'one two three' to '123'."
    )

    expiry_month: Optional[int] = Field(
        default=None,
        description="Card expiry month converted to an integer from 1 to 12. For example, '12/27' is 12. 'December' is 12."
    )

    expiry_year: Optional[int] = Field(
        default=None,
        description="Card expiry year converted to a four-digit integer. For example, '12/27' MUST be converted to 2027."
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
        model: str = "gpt-5.4-nano",
    ):
        self.client = client or OpenAI()
        self.model = model

    def extract(self, user_input: str, current_stage: str, balance_context, safe_state_json) -> ExtractionResult:
        """
        Extract structured fields from one user message.
        """

        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": get_extraction_prompt(current_stage, balance_context, safe_state_json),
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