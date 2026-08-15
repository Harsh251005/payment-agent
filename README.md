# Production-Ready Payment Collection AI Agent

This repository contains a robust, conversational AI agent designed to handle an end-to-end payment collection flow.

It utilizes a **hybrid architecture**: a strict, deterministic state machine enforces business rules, API payloads, validation, and security constraints, while an LLM using **Structured Outputs** handles natural-language extraction, coreference resolution, and empathetic response generation.

## Architecture

The agent follows a hybrid design:

* **Deterministic state machine** — controls business logic, validation, verification attempts, payment flow, and terminal states.
* **LLM-based extraction** — extracts entities such as account ID, name, DOB, PIN code, card details, and payment amount from natural language.
* **Structured Outputs** — ensures extracted information follows predefined schemas.
* **Deterministic validation** — validates sensitive fields and enforces strict identity verification rules.
* **API integration layer** — handles account lookup and payment processing independently from conversational logic.
* **State management** — preserves conversation context across multiple turns and supports out-of-order information.

This architecture ensures that the LLM is responsible for understanding language, while critical business and security decisions remain deterministic.

## Project Structure

```text
payment-agent/
├── agent.py          # Core Agent class and conversation orchestration
├── models.py         # Pydantic schemas and data models
├── parser.py         # LLM-driven entity extraction
├── prompts.py        # State-aware extraction and response prompts
├── state.py          # ConversationState management
├── tools.py          # Payment/account API integrations
├── validators.py     # Deterministic validation and identity verification
├── main.py           # Interactive CLI
├── evaluation.py     # Automated evaluation suite
├── requirements.txt  # Python dependencies
└── README.md         # Project documentation
```

### File Responsibilities

| File            | Responsibility                                                                               |
|-----------------| -------------------------------------------------------------------------------------------- |
| `agent.py`      | Orchestrates the conversation, state machine, validation, API calls, and response generation |
| `models.py`     | Defines strict Pydantic schemas and data structures                                          |
| `parser.py`     | Uses the LLM to extract structured entities from user messages                               |
| `prompts.py`    | Contains dynamic prompts that adapt to the current conversation state                        |
| `state.py`      | Stores and manages conversation state across turns                                           |
| `tools.py`      | Provides account lookup and payment processing API integrations                              |
| `validators.py` | Performs deterministic validation and identity verification                                  |
| `main.py`       | Provides an interactive CLI for manually testing the agent                                   |
| `evaluation.py` | Runs automated evaluation scenarios and edge-case tests                                      |

## Key Features

### Conversational Entity Extraction

The LLM can extract multiple entities from a single message, including:

* Account ID
* Customer name
* Date of birth
* PIN code
* Aadhaar last four digits
* Payment amount
* Card number
* CVV
* Card expiry
* Cardholder name

The user does not have to provide information in a predefined order.

### Out-of-Order Information

Users can provide multiple pieces of information at once, even when the agent has not explicitly asked for them.

For example:

```text
ACC1001. My name is Nithin Jain, and my pincode is 400001. I want to pay 500.
```

The agent extracts all relevant information and skips questions for fields that have already been provided.

### Coreference Resolution

The agent can resolve references such as:

```text
Name is the same as my account name.
```

and map them to the appropriate previously collected entity.

### Strict Identity Verification

Identity verification is deterministic and protected by retry limits.

The agent prevents further verification attempts once the maximum number of failed attempts has been reached.

### Graceful API Failure Recovery

Payment failures are interpreted using specific API error codes.

For example:

* `invalid_card`
* `insufficient_balance`

The agent rejects only the affected field and allows the user to correct it without unnecessarily restarting the entire flow.

### Secure State Management

Critical security and business decisions are never delegated entirely to the LLM.

The deterministic state machine controls:

* Verification status
* Retry limits
* Account lookup
* Outstanding balance validation
* Payment amount validation
* Payment processing
* Terminal lockout states

### Drip-Feed Conversations

Users can provide payment information incrementally across multiple messages.

For example:

```text
CVV is 123
```

followed later by:

```text
Expiry is 12/27
```

and finally:

```text
Card number is 4532015112830366
```

The agent maintains the collected information and only requests the remaining fields.

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Harsh251005/payment-agent.git
cd payment-agent
```

### 2. Create and Activate a Virtual Environment

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the OpenAI API Key

#### macOS / Linux

```bash
export OPENAI_API_KEY="your_actual_api_key_here"
```

#### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your_actual_api_key_here"
```

## Running the Project

### Interactive CLI

Run the agent interactively and test conversations manually:

```bash
python main.py
```

### Automated Evaluation

Run the automated evaluation suite:

```bash
python evaluation.py
```

The evaluation suite covers scenarios such as:

* Successful payment flows
* Out-of-order entity extraction
* Identity verification failures
* Verification lockouts
* Invalid card recovery
* Insufficient balance
* Drip-fed payment information
* Coreference resolution
* Leap-year and date-related edge cases

## Sample Conversations

### 1. Successful End-to-End Payment

**Scenario:** Happy path with multiple entities provided out of order and a coreference reference.

**User:**

```text
Hi, I need to make a payment for my account.
```

**Agent:**

```text
Hi, I can help with that. Please share your account ID so I can look up your account and continue with the payment.
```

**User:**

```text
It's ACC1001. My name is Nithin Jain, and my pincode is 400001. I want to pay 500.
```

**Agent:**

```text
Thanks, Nithin — I’ve noted the amount of ₹500. To proceed with the card payment, please provide the missing card details: card number, CVV, and expiry date.
```

**User:**

```text
Card is 4532 0151 1283 0366, CVV is 123, expires 12/27. Name is the same as my account name.
```

**Agent:**

```text
Thanks — I’ve received your payment details and the payment has been successfully processed. Your transaction ID is txn_1786817872463_dae5orx, and your account is now up to date.
```

### 2. Verification Failure and Terminal Lockout

**Scenario:** The user exhausts the allowed verification attempts.

**User:**

```text
ACC1002
```

**Agent:**

```text
Thanks — I have your account reference. To continue verification, please provide your full name.
```

**User:**

```text
My name is Rajarajeswari Balasubramaniam
```

**Agent:**

```text
Thanks, Rajarajeswari Balasubramaniam. To continue verification, please provide either your Date of Birth, your PIN code, or the last 4 digits of your Aadhaar.
```

**User:**

```text
My pincode is 400001
```

**Agent:**

```text
Thanks for sharing your pincode. I’m unable to verify your identity with the details provided, so we’ll need to stop this verification attempt for now. Please try again with the required verification details when you’re ready.
```

**User:**

```text
Wait, DOB is 1985-11-22
```

**Agent:**

```text
Thanks — I’ve noted that you’ve confirmed your date of birth. Unfortunately, I still can’t verify your identity right now, so we’ll need to stop this verification attempt here.
```

**User:**

```text
Okay, let me try my Aadhaar, it ends in [Aadhaar Redacted]
```

**Agent:**

```text
I understand you’d like to try your Aadhaar, but I can’t continue verification here because the verification process has been terminated. Please contact support or restart the verification flow to continue.
```

**User:**

```text
Please let me try one more time, pincode is 400002!
```

**Agent:**

```text
I’m sorry, but I can’t continue this verification or payment flow any further. Please contact the support team or use the official payment portal to proceed.
```

### 3. Payment Failure Recovery

**Scenario:** The user provides an amount above the outstanding balance and then supplies an invalid card number.

**User:**

```text
Hello, ACC1001, Nithin Jain, DOB 1990-05-14
```

**Agent:**

```text
Thanks, Nithin — I’ve got your verified details. Please tell me the payment amount you’d like to pay, and I’ll take it from there.
```

**User:**

```text
I want to pay 2000
```

**Agent:**

```text
The amount you want to pay, ₹2000, exceeds your outstanding balance of ₹1250.75. Please enter an amount up to ₹1250.75 to continue.
```

**User:**

```text
Oops, make it 1000.
```

**Agent:**

```text
Got it — I’ve updated the amount to ₹1000. Please provide the remaining card details: card number, CVV, and expiry date.
```

**User:**

```text
Card is 4000 0000 0000 0000, expiry 12/27, CVV 123, cardholder Nithin Jain
```

**Agent:**

```text
Thanks, Nithin — I’ve received the expiry, CVV, and cardholder name, but the card number appears invalid. Please re-enter the full card number carefully so I can continue.
```

**User:**

```text
Ah, sorry, the card is 4532015112830366
```

**Agent:**

```text
Thanks — your payment of ₹1000 has been received successfully, and the transaction is complete. Your transaction ID is txn_1786817903126_7g8kmmc; if you’d like, I can now help with the next step for your account.
```

### 4. Name Collision and Drip-Feed

**Scenario:** Payment details are provided one field at a time, and an explicitly supplied cardholder name overrides any inferred value.

**User:**

```text
ACC1002
```

**Agent:**

```text
Thanks — I have your account reference. To continue, please share your full name exactly as it appears on the account.
```

**User:**

```text
Rajarajeswari Balasubramaniam
```

**Agent:**

```text
Thanks, Rajarajeswari Balasubramaniam. To continue verification, please provide either your Date of Birth, your PIN code, or the last 4 digits of your Aadhaar.
```

**User:**

```text
pincode is 400002
```

**Agent:**

```text
Thanks, I’ve noted your pincode. Your balance due is ₹540.00, so please tell me the payment amount you’d like to pay next.
```

**User:**

```text
pay 100
```

**Agent:**

```text
Thanks — I can take the ₹100 payment, but I still need your card number, CVV, and expiry date to continue.
```

**User:**

```text
cvv is 123
```

**Agent:**

```text
Thanks — I’ve got the CVV. I still need the card number and expiry date to continue with the payment.
```

**User:**

```text
expiry is 12/27
```

**Agent:**

```text
Thanks — I’ve noted the expiry date as 12/27. I still need your card number to continue with the payment.
```

**User:**

```text
card number is 4532015112830366
```

**Agent:**

```text
Thanks — I have the card number. Please provide the remaining card field: cardholder name.
```

**User:**

```text
The name on the card is actually Raja B
```

**Agent:**

```text
Thanks, Raja B — your payment of ₹100.00 has been received successfully, and your transaction ID is txn_1786820237179_hhavw96. Your remaining balance is ₹540.00; if you’d like, you can continue with the next payment step.
```

## Design Principles

This project intentionally separates **language understanding** from **business-critical execution**.

The LLM is used for tasks where language understanding is valuable:

```text
User Message
     │
     ▼
LLM Structured Extraction
     │
     ▼
Structured Entities
     │
     ▼
Deterministic Validation
     │
     ▼
Conversation State Machine
     │
     ├── Account Lookup
     ├── Identity Verification
     ├── Amount Validation
     ├── Payment Processing
     └── Terminal / Recovery States
     │
     ▼
Response Generation
     │
     ▼
User
```

This approach reduces the risk of allowing an LLM to directly make security-sensitive or financial decisions while still providing a natural conversational experience.

## Testing

Run the complete evaluation suite with:

```bash
python evaluation.py
```

The tests are designed to verify both normal operation and failure recovery, including:

* Happy-path payments
* Missing fields
* Out-of-order information
* Multiple entities in a single message
* Coreference resolution
* Invalid card details
* API failures
* Insufficient balance
* Verification failures
* Retry limits
* Terminal lockout
* Incremental / drip-fed inputs
* Date validation edge cases
* Leap-year scenarios

## Security Considerations

The project follows a **deterministic-first** approach for security-sensitive operations.

In particular:

* The LLM does not decide whether an identity is verified.
* Verification retry limits are enforced by deterministic code.
* Payment amount limits are validated against the account balance.
* Invalid payment fields are rejected without unnecessarily discarding valid fields.
* Terminal states cannot be bypassed through additional natural-language input.
* Sensitive identifiers can be redacted from logs and user-facing outputs where appropriate.

## Future Improvements

Potential extensions include:

* Persistent conversation storage
* Production payment gateway integration
* Authentication and authorization layers
* Structured observability and tracing
* LLM evaluation and regression testing
* Rate limiting and abuse detection
* Improved PII handling and redaction
* Multi-channel interfaces such as WhatsApp or web chat
* Human handoff and support escalation
* Production-grade audit logging

---

Built as a demonstration of a **production-oriented hybrid AI agent architecture**, combining LLM-based conversational intelligence with deterministic business logic and security controls.

---

### Author

**Harsh Dharnidharka**  
[GitHub](https://github.com/Harsh251005) | [LinkedIn](https://www.linkedin.com/in/harsh-dharnidharka/)

---