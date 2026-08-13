from parser import InputParser


def main():
    parser = InputParser()

    test_inputs = [
        "it's acc 1001"
        "My full name is Nithin Jain and DOB is May 14, 1990"
        "I wanna clear a thousand"
        "card ends? No, full card is 4532 0151 1283 0366"
        "expiry is 12 slash 27"
        "three two one is my CVV"
    ]

    for user_input in test_inputs:
        print(f"\nUser: {user_input}")

        result = parser.extract(user_input)

        print("Extracted:")
        print(result.model_dump())


if __name__ == "__main__":
    main()