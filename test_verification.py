from validators import verify_identity
from agent import Agent


def test_verification_with_dob():
    assert verify_identity(
        user_name="Nithin Jain",
        user_dob="1990-05-14",
        user_aadhaar_last4=None,
        user_pincode=None,
        account_name="Nithin Jain",
        account_dob="1990-05-14",
        account_aadhaar_last4="4321",
        account_pincode="400001",
    ) is True


def test_verification_with_aadhaar():
    assert verify_identity(
        user_name="Nithin Jain",
        user_dob=None,
        user_aadhaar_last4="4321",
        user_pincode=None,
        account_name="Nithin Jain",
        account_dob="1990-05-14",
        account_aadhaar_last4="4321",
        account_pincode="400001",
    ) is True


def test_verification_with_pincode():
    assert verify_identity(
        user_name="Nithin Jain",
        user_dob=None,
        user_aadhaar_last4=None,
        user_pincode="400001",
        account_name="Nithin Jain",
        account_dob="1990-05-14",
        account_aadhaar_last4="4321",
        account_pincode="400001",
    ) is True


def test_wrong_name():
    assert verify_identity(
        user_name="Nitin Jain",
        user_dob="1990-05-14",
        user_aadhaar_last4=None,
        user_pincode=None,
        account_name="Nithin Jain",
        account_dob="1990-05-14",
        account_aadhaar_last4="4321",
        account_pincode="400001",
    ) is False


def test_case_sensitive_name():
    assert verify_identity(
        user_name="nithin jain",
        user_dob="1990-05-14",
        user_aadhaar_last4=None,
        user_pincode=None,
        account_name="Nithin Jain",
        account_dob="1990-05-14",
        account_aadhaar_last4="4321",
        account_pincode="400001",
    ) is False


def test_wrong_secondary_factor():
    assert verify_identity(
        user_name="Nithin Jain",
        user_dob="1991-05-14",
        user_aadhaar_last4=None,
        user_pincode=None,
        account_name="Nithin Jain",
        account_dob="1990-05-14",
        account_aadhaar_last4="4321",
        account_pincode="400001",
    ) is False


def test_name_matches_but_no_secondary_factor():
    assert verify_identity(
        user_name="Nithin Jain",
        user_dob=None,
        user_aadhaar_last4=None,
        user_pincode=None,
        account_name="Nithin Jain",
        account_dob="1990-05-14",
        account_aadhaar_last4="4321",
        account_pincode="400001",
    ) is False


def test_successful_verification():
    agent = Agent()

    response = agent.next("Hi")

    assert "account ID" in response["message"]

    response = agent.next(
        "my account number is ACC1001"
    )

    assert "full name" in response["message"].lower()

    response = agent.next(
        "My name is Nithin Jain"
    )

    assert "date of birth" in response["message"].lower()

    response = agent.next(
        "I was born on 14th May 1990"
    )

    assert agent.state.verified is True
    assert "₹1250.75" in response["message"]

def test_verification_retry_limit():
    agent = Agent()

    agent.next("Hi")
    agent.next("My account is ACC1001")

    # Attempt 1
    response = agent.next(
        "My name is Wrong Name and my DOB is 1990-05-14"
    )

    assert agent.state.verification_attempts == 1

    # Attempt 2
    response = agent.next(
        "My name is Wrong Name and my DOB is 1990-05-14"
    )

    assert agent.state.verification_attempts == 2

    # Attempt 3
    response = agent.next(
        "My name is Wrong Name and my DOB is 1990-05-14"
    )

    assert agent.state.verification_attempts == 3
    assert "can't continue" in response["message"]