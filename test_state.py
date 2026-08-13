from models import AgentStage
from state import ConversationState


def main():
    state = ConversationState()

    print("Initial state:")
    print(state)

    state.stage = AgentStage.ACCOUNT_LOOKUP
    state.account_id = "ACC1001"

    state.identity.full_name = "Nithin Jain"

    print("\nUpdated state:")
    print(state)

    assert state.stage == AgentStage.ACCOUNT_LOOKUP
    assert state.account_id == "ACC1001"
    assert state.identity.full_name == "Nithin Jain"
    assert state.verified is False

    print("\nState test passed.")


if __name__ == "__main__":
    main()