from agent import Agent


def test_account_lookup_flow():
    agent = Agent()

    response = agent.next("Hi")

    assert "account ID" in response["message"]

    response = agent.next(
        "yeah my account number is ACC1001 I think"
    )

    assert "full name" in response["message"].lower()

    assert agent.state.account_id == "ACC1001"
    assert agent.state.account is not None


def test_account_not_found():
    agent = Agent()

    agent.next("Hi")

    response = agent.next(
        "My account ID is ACC9999"
    )

    assert "couldn't find an account" in response["message"].lower()
    assert agent.state.account is None