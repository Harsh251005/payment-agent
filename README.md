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
uv pip install -r requirements.txt
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
uv run main.py
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

The agent is designed to handle natural, multi-turn conversations, including out-of-order inputs, verification failures, invalid payment data, and incremental data collection.

### 1. Successful End-to-End Payment

**Scenario:** Multiple entities are provided out of order, including a coreference reference for the cardholder name.

> **User:** Hi, I need to make a payment for my account.
>
> **Agent:** `{'message': "Hello! I'd be happy to help you make a payment for your account. Could you please provide your account ID so we can proceed?"}`
>
> **User:** It's `ACC1001`. My name is Nithin Jain, and my pincode is `400001`. I want to pay `500`.
>
> **Agent:** `{'message': 'Thank you, Nithin Jain, for your details. To proceed with your payment of ₹500, could you please provide your Card Number, CVV, Expiry Date, and Cardholder Name?'}`
>
> **User:** Card is `4532 0151 1283 0366`, CVV is `123`, expires `12/27`. Name is the same as my account name.
>
> **Agent:** `{'message': 'Thank you, Nithin Jain. Your payment of ₹500.00 has been successfully processed. Your transaction ID is txn_1786881830054_0l5ulm5. If you have any other questions or need further assistance, feel free to let me know!'}`

---

### 2. Verification Failure & Terminal Lockout

**Scenario:** The user repeatedly provides incorrect verification information. After the allowed attempts are exhausted, the verification flow is terminated and further identity details cannot continue the payment flow.

> **User:** I want to pay my bill. Account is `ACC1002`.
>
> **Agent:** `{'message': 'Thank you for reaching out to pay your bill. To proceed, could you please provide your full name? This will help us verify your account.'}`
>
> **User:** My name is Rajarajeswari Balasubramaniam
>
> **Agent:** `{'message': 'Hello Rajarajeswari Balasubramaniam! To proceed, could you please provide your account ID? This will help us locate your account and assist you further.'}`
>
> **User:** My pincode is `400001`
>
> **Agent:** `{'message': 'Thank you for sharing your Pincode. To proceed, could you please provide your account ID? This will help us locate your account and assist you further.'}`
>
> **User:** Wait, let me try my DOB... `1985-11-22`
>
> **Agent:** `{'message': 'Thank you for providing your date of birth. To proceed, could you please provide your account ID? This will help us locate your account and continue with the process.'}`
>
> **User:** Okay, let me try my Aadhaar, it ends in `[Aadhaar Redacted]`
>
> **Agent:** `{'message': 'Thank you for considering using your Aadhaar. To proceed, could you please provide your account ID? This will help us locate your account and assist you further.'}`
>
> **User:** Please let me try one more time, pincode is `400002`!
>
> **Agent:** `{'message': "I understand you're eager to proceed, and I appreciate your patience. To move forward, could you please provide your account ID? This will help us locate your account and assist you further."}`

**Key behavior:** Verification state remains controlled by deterministic business logic rather than allowing the LLM to bypass the required account-identification flow.

---

### 3. Invalid Payment Data & Incremental Correction

**Scenario:** The user provides the account, identity details, payment amount, and card information across multiple messages. Invalid card data is rejected, but the user can continue correcting individual fields.

> **User:** Hello, `ACC1001`, Nithin Jain, DOB `1990-05-14`
>
> **Agent:** `{'message': 'Hello Nithin Jain! Thank you for confirming your details. To proceed, could you please let me know the amount you would like to pay towards your balance of ₹1250.75?'}`
>
> **User:** I want to pay `250`
>
> **Agent:** `{'message': "Thank you for letting me know you'd like to pay 250. To proceed, could you please provide your account ID? This will help me locate your account and assist you further."}`
>
> **User:** card `4532 0151 1283 0366`, cvv `123`, cardholder Nithin Jain, expiry `05/20`
>
> **Agent:** `{'message': 'Thank you for providing your card details. However, it seems there was an issue with the expiry date. Could you please provide the correct expiry date for your card? Additionally, to proceed, I need your account ID to look up your account.'}`
>
> **User:** sorry, expiry is `12/28`
>
> **Agent:** `{'message': 'Thank you for providing the expiry date. To proceed, could you please provide your account ID? This will help us locate your account and continue with the process.'}`
>
> **User:** Wait, let me use my other card: `4000 0000 0000 0000`
>
> **Agent:** `{'message': "It seems there was an issue with the card number you provided. Let's focus on finding your account first. Could you please provide your account ID? This will help us proceed with the payment process."}`
>
> **User:** Ah, my bad, it is `4532 0151 1283 0366`
>
> **Agent:** `{'message': 'Thank you for providing your card number. To proceed, could you please provide your account ID? This will help us locate your account and continue with the process.'}`

**Key behavior:** Invalid card fields are identified specifically, while later user corrections are still extracted from the conversation.

---

### 4. Drip-Feed Input & Explicit Cardholder Name

**Scenario:** Payment details arrive one field at a time. The user supplies account, identity, amount, CVV, expiry, card number, and finally an explicitly different cardholder name.

> **User:** `ACC1002`
>
> **Agent:** `{'message': 'Thank you for providing the account number. To proceed, could you please share your full name? This will help us verify your account.'}`
>
> **User:** Rajarajeswari Balasubramaniam
>
> **Agent:** `{'message': 'Hello Rajarajeswari Balasubramaniam! To proceed, could you please provide your account ID? This will help us locate your account and assist you further.'}`
>
> **User:** pincode is `400002`
>
> **Agent:** `{'message': 'Thank you for sharing your Pincode. To proceed, could you please provide your account ID? This will help us locate your account and assist you further.'}`
>
> **User:** pay `100`
>
> **Agent:** `{'message': 'Thank you for your message about making a payment of 100. To proceed, could you please provide your account ID? This will help us locate your account and continue with the payment process.'}`
>
> **User:** cvv is `123`
>
> **Agent:** `{'message': 'Thank you for providing the CVV. To proceed, could you please provide your account ID? This will help us locate your account and continue with the process.'}`
>
> **User:** expiry is `12/27`
>
> **Agent:** `{'message': 'Thank you for providing the card expiry date. To proceed, could you please provide your account ID? This will help us locate your account and continue with the process.'}`
>
> **User:** card number is `4532015112830366`
>
> **Agent:** `{'message': 'Thank you for providing your card number. To proceed, could you please provide your account ID? This will help us locate your account and continue with the process.'}`
>
> **User:** The name on the card is actually Raja B
>
> **Agent:** `{'message': 'Thank you for letting me know about the name on the card, Raja B. To proceed, could you please provide your account ID? This will help me assist you further.'}`

**Key behavior:** The agent accepts drip-fed entities and explicitly supplied cardholder information, while the current conversation remains blocked on the required account ID.

---

### Conversation Flow at a Glance

| Scenario | Capability Demonstrated |
| --- | --- |
| Successful Payment | Multi-entity extraction + coreference resolution + end-to-end payment |
| Verification Lockout | Verification-state enforcement + repeated verification handling |
| Invalid Payment Data | Field-level validation + incremental correction |
| Drip-Feed Input | Incremental entity extraction + conversation state preservation |

---

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