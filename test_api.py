from tools import PaymentAPI, PaymentAPIError
from decimal import Decimal

def main():
    api = PaymentAPI()

    try:
        account = api.lookup_account("ACC1001")

        result = api.process_payment(
            account_id="ACC1001",
            amount=Decimal("500.00"),
            cardholder_name="Nithin Jain",
            card_number="4532015112830366",
            cvv="123",
            expiry_month=12,
            expiry_year=2027,
        )

        print("Lookup successful:")
        print(account)

        print("Payment successful:")
        print(result)

    except PaymentAPIError as exc:
        print(f"Lookup failed: {exc}")


if __name__ == "__main__":
    main()