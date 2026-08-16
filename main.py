import sys
from agent import Agent


def main():
    print("=" * 65)
    print("   Prodigal Payment Collection AI Agent - Interactive CLI")
    print("   Type 'exit' or 'quit' to end the session.")
    print("=" * 65)

    # Initialize the agent
    try:
        agent = Agent()
    except Exception as e:
        print(f"\n[System Error] Failed to initialize the Agent: {e}")
        print("Please ensure your environment variables (e.g., OPENAI_API_KEY) are set.")
        sys.exit(1)

    # Bootstrapping the first message naturally
    print("\nAgent: Hello! Please share your account ID to get started.")

    while True:
        try:
            # Capture user input
            user_input = input("\nUser : ").strip()

            # Handle exit commands
            if user_input.lower() in ['exit', 'quit']:
                print("\n[System] Terminating session. Goodbye!")
                break

            # Process the input through your state machine and LLM
            response = agent.next(user_input)

            # Display the generated response
            print(f"Agent: {response}")

        except KeyboardInterrupt:
            # Handles the user pressing Ctrl+C cleanly without throwing an ugly traceback
            print("\n\n[System] Session interrupted by user (Ctrl+C). Goodbye!")
            break
        except Exception as e:
            # Safety net so the CLI doesn't crash during a live demo
            print(f"\n[System Error] An unexpected error occurred: {e}")
            print("Please try again or restart the session.")


if __name__ == "__main__":
    main()