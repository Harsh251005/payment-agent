from agent import Agent

all_tests = {
    "1. Messy Human (Happy Path)": [
        "Hi, I need to make a payment for my account.",
        "It's ACC1001. My name is Nithin Jain, and my pincode is 400001. I want to pay 500.",
        "Card is 4532 0151 1283 0366, CVV is 123, expires 12/27. Name is the same as my account name."
    ],

    "2. Strict Verification Lockout (3 Strikes)": [
        "ACC1002",
        "My name is Rajarajeswari Balasubramaniam",
        "My pincode is 400001",  # Strike 1 (Actual is 400002)
        "Wait, DOB is 1985-11-22",  # Strike 2 (Actual is 23rd)
        "Okay, let me try my Aadhaar, it ends in [Aadhaar Redacted]",  # Strike 3 (Terminal failure)
        "Please let me try one more time, pincode is 400002!"  # The agent MUST refuse
    ],

    "3. API Error Recovery (Invalid Card)": [
        "Hello, ACC1001, Nithin Jain, DOB 1990-05-14",
        "I want to pay 2000",  # Error: Exceeds balance of 1250.75
        "Oops, make it 1000.",  # Recovers
        "Card is 4000 0000 0000 0000, expiry 12/27, CVV 123, cardholder Nithin Jain",  # API Error: Invalid card
        "Ah, sorry, the card is 4532015112830366"  # Recovers and processes
    ],

    "4. The Leap Year Trap (Calendar Math)": [
        "Account ACC1004",
        "Rahul Mehta",
        "I was born on Feb 29, 1988",  # Leap year date format
        "pay the full amount",  # Dynamic balance extraction
        "card number 4532015112830366, expiry 12/2027, cvv 123, name Rahul Mehta"
    ],

    "5. The Drip Feed and Name Collision": [
        "ACC1002",
        "Rajarajeswari Balasubramaniam",
        "pincode is 400002",
        "pay 100",
        "cvv is 123",
        "expiry is 12/27",
        "card number is 4532015112830366",
        "The name on the card is actually Raja B"  # Overwrites default identity name
    ],

    "6. Early Lookup Failures": [
        "My account is potato",  # Format error
        "Sorry, ACC9999",  # API 404 Not Found error
        "Okay, my bad, it is ACC1001",  # Recovers
        "Nithin Jain"
    ]
}

for test_name, messages in all_tests.items():
    print(f"\n{'=' * 20} RUNNING TEST: {test_name} {'=' * 20}")

    # Instantiate a fresh Agent for each test to prevent state bleeding
    a = Agent()

    for message in messages:
        print(f"User: {message}")

        # Added a try-except block so one failing test doesn't stop the whole suite
        try:
            response = a.next(message)
            print(f"Agent: {response.get('message', 'NO MESSAGE KEY RETURNED')}")
        except Exception as e:
            print(f"Agent CRASHED: {e}")
            break

        print("-" * 50)