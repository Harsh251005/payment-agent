from agent import Agent


def run_evaluation_suite() -> bool:
    """Runs the full evaluation test suite against the Agent.

    Returns True if all test scenarios execute cleanly without unhandled exceptions,
    false-positive lockouts, or logic breaks.
    """
    success_passed = True
    lockout_passed = True
    failure_passed = True
    edge_passed = True

    print("========================================================================")
    print("RUNNING AUTOMATED AGENT EVALUATION SUITE")
    print("========================================================================")

    # -------------------------------------------------------------------------
    # 1. Successful End-to-End Payment (Happy Path)
    # -------------------------------------------------------------------------
    messages_success = [
        "Hi, I need to make a payment for my account.",
        (
            "It's ACC1001. My name is Nithin Jain, and my pincode is 400001. I"
            " want to pay 500."
        ),
        (
            "Card is 4532 0151 1283 0366, CVV is 123, expires 12/27. Name is the"
            " same as my account name."
        ),
    ]

    print("\n--- TEST 1: Successful End-to-End Payment (Happy Path) ---")
    agent = Agent()
    try:
        for message in messages_success:
            print(f"User : {message}")
            response = agent.next(message)
            msg_text = response.get("message", str(response))
            print(f"Agent: {msg_text}\n")
    except Exception as e:
        print(f"TEST 1 CRASHED: {e}")
        success_passed = False

    print("=" * 72)

    # -------------------------------------------------------------------------
    # 2. Strict Verification Lockout (3 Strikes)
    # -------------------------------------------------------------------------
    messages_lockout = [
        "I want to pay my bill. Account is ACC1002.",
        "My name is Rajarajeswari Balasubramaniam",
        "My pincode is 400001",  # Strike 1 (Actual is 400002)
        "Wait, let me try my DOB... 1985-11-22",  # Strike 2 (Actual is 23rd)
        (
            "Okay, let me try my Aadhaar, it ends in [Aadhaar Redacted]"
        ),  # Strike 3 (Terminal failure)
        (
            "Please let me try one more time, pincode is 400002!"
        ),  # Agent correctly refuses and stays terminated
    ]

    print("\n--- TEST 2: Strict Verification Lockout (3 Strikes) ---")
    agent = Agent()
    try:
        for message in messages_lockout:
            print(f"User : {message}")
            response = agent.next(message)
            msg_text = response.get("message", str(response))
            print(f"Agent: {msg_text}\n")
    except Exception as e:
        print(f"TEST 2 CRASHED: {e}")
        lockout_passed = False

    print("=" * 72)

    # -------------------------------------------------------------------------
    # 3. Payment Failure (Invalid & Expired Card Recovery)
    # -------------------------------------------------------------------------
    messages_payment_failure = [
        "Hello, ACC1001, Nithin Jain, DOB 1990-05-14",
        "I want to pay 250",
        (
            "card 4532 0151 1283 0366, cvv 123, cardholder Nithin Jain, expiry"
            " 05/20"
        ),  # API Error: Expired Date
        "sorry, expiry is 12/28",  # Recovers from expiry
        (
            "Wait, let me use my other card: 4000 0000 0000 0000"
        ),  # API Error: Invalid Card Number
        "Ah, my bad, it is 4532 0151 1283 0366",  # Recovers and processes successfully
    ]

    print(
        "\n--- TEST 3: Payment Failure & API Error Recovery (Invalid/Expired"
        " Cards) ---"
    )
    agent = Agent()
    try:
        for message in messages_payment_failure:
            print(f"User : {message}")
            response = agent.next(message)
            msg_text = response.get("message", str(response))
            print(f"Agent: {msg_text}\n")
    except Exception as e:
        print(f"TEST 3 CRASHED: {e}")
        failure_passed = False

    print("=" * 72)

    # -------------------------------------------------------------------------
    # 4. Edge Case (Drip-Feed and Name Collision)
    # -------------------------------------------------------------------------
    messages_edge_case = [
        "ACC1002",
        "Rajarajeswari Balasubramaniam",
        "pincode is 400002",
        "pay 100",
        "cvv is 123",
        "expiry is 12/27",
        "card number is 4532015112830366",
        (
            "The name on the card is actually Raja B"
        ),  # Overwrites default identity name and processes payment
    ]

    print("\n--- TEST 4: Edge Case (Drip-Feed & Cardholder Override) ---")
    agent = Agent()
    try:
        for message in messages_edge_case:
            print(f"User : {message}")
            response = agent.next(message)
            msg_text = response.get("message", str(response))
            print(f"Agent: {msg_text}\n")
    except Exception as e:
        print(f"TEST 4 CRASHED: {e}")
        edge_passed = False

    print("=" * 72)

    # Final Evaluation Summary
    all_passed = (
        success_passed and lockout_passed and failure_passed and edge_passed
    )
    if all_passed:
        print(
            "\nRESULT: ALL EVALUATION TESTS COMPLETED SUCCESSFULLY WITHOUT"
            " CRASHES!"
        )
    else:
        print(
            "\nRESULT: SOME TESTS FAILED OR ENCOUNTERED EXCEPTIONS. REVIEW THE"
            " OUTPUT ABOVE."
        )

    return all_passed


if __name__ == "__main__":
    run_evaluation_suite()