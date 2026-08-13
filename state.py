from dataclasses import dataclass, field
from typing import Optional

from models import (
    AccountData,
    AgentStage,
    PaymentData,
    UserIdentityData,
)


@dataclass
class ConversationState:
    """
    Complete state of one Agent conversation.

    A single Agent instance owns one ConversationState and
    updates it after every call to next().
    """

    stage: AgentStage = AgentStage.START

    account_id: Optional[str] = None
    account: Optional[AccountData] = None

    identity: UserIdentityData = field(
        default_factory=UserIdentityData
    )

    verification_attempts: int = 0
    verified: bool = False

    payment: PaymentData = field(
        default_factory=PaymentData
    )

    transaction_id: Optional[str] = None
    last_error: Optional[str] = None