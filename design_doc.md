# System Design: AI Payment Collection Agent

## 1. Architecture Overview

The **AI Payment Collection Agent** uses a **Hybrid AI Architecture** that combines deterministic business logic with LLM-powered natural language understanding.

The core design principle is simple:

> **Let the LLM understand the user. Let deterministic code control the money.**

This separation ensures that conversational flexibility does not compromise payment correctness, identity verification, or security.

### High-Level Architecture

```text
                         ┌──────────────────────┐
                         │      User Input      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     InputParser      │
                         │  LLM + Structured    │
                         │      Outputs         │
                         └──────────┬───────────┘
                                    │
                           Extracted Entities
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │       Deterministic Agent    │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │   ConversationState    │  │
                    │  └────────────────────────┘  │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │      Validators        │  │
                    │  └────────────────────────┘  │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │    State Transitions   │  │
                    │  └────────────────────────┘  │
                    └──────────────┬───────────────┘
                                   │
                       Validated State / Errors
                                   │
                                   ▼
                         ┌──────────────────────┐
                         │   Response Generator │
                         │      prompts.py      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Conversational     │
                         │      Response        │
                         └──────────────────────┘
```

### Component Responsibilities

| Component           | Responsibility                                                             |
| ------------------- | -------------------------------------------------------------------------- |
| `Agent`             | Orchestrates the complete conversation and deterministic state transitions |
| `ConversationState` | Maintains verified session data and current workflow state                 |
| `Validators`        | Performs deterministic validation and identity verification                |
| `InputParser`       | Converts natural-language input into structured entities                   |
| `prompts.py`        | Generates contextual, empathetic responses based on deterministic state    |
| API Layer           | Handles account lookup and payment processing                              |

### Deterministic Workflow

The payment journey follows a controlled sequence:

```text
Lookup
   │
   ▼
Verification
   │
   ▼
Payment
   │
   ▼
Completed
```

At every stage, the deterministic state machine decides what actions are permitted.

The LLM cannot:

* Skip identity verification
* Override retry limits
* Trigger payment processing on its own
* Change account balances
* Mark an identity as verified
* Bypass a terminal state

Instead, the LLM is responsible only for **language understanding and response generation**.

---

## 2. State & Memory Management

Reliable context management is critical in conversational payment systems because users rarely provide information in a perfectly structured order.

The system therefore uses a **dual-memory approach**.

### 2.1 Persistent Memory — `ConversationState`

`ConversationState` is a strictly typed dataclass that persists for the lifetime of the conversation.

Once information has been deterministically validated, it becomes part of the trusted conversation state.

Typical state information includes:

```text
Account ID
Customer Name
Date of Birth
PIN Code
Aadhaar Last 4
Payment Amount
Card Number
CVV
Card Expiry
Cardholder Name
Verification Status
Retry Count
Payment Status
```

The state machine uses this information to determine:

* What information has already been collected
* What information is still missing
* Which workflow stage the user is currently in
* Whether verification is complete
* Whether further attempts are permitted
* Whether payment processing can be triggered

### 2.2 Ephemeral Context — LLM Extraction Context

A conventional entity extractor typically processes each user message independently.

That creates problems with contextual statements such as:

```text
Use the same name for the card.
```

or:

```text
The expiry is the same as before.
```

The current message may contain no explicit value, making isolated extraction unreliable.

To solve this, the agent serializes the relevant deterministic state into a **safe JSON representation** and injects that context into the `InputParser` prompt on every turn.

Conceptually:

```text
Current User Message
        +
Verified Conversation State
        │
        ▼
   LLM Extractor
        │
        ▼
Structured Entities
```

This enables the LLM to resolve:

* Pronouns
* References to previously supplied information
* "Same as before" statements
* Account-name → cardholder-name relationships
* Incrementally supplied payment information

The important distinction is that the LLM **reads** state context but does not independently modify trusted state. Deterministic validation remains the authority.

---

## 3. Key Design Decisions & Tradeoffs

### Decision 1 — Deterministic Verification Instead of LLM Verification

#### Problem

Identity verification is security-sensitive and must use exact matching.

An LLM-based verifier could potentially perform fuzzy reasoning such as:

```text
User DOB: 1985-11-23
Account DOB: 1985-11-22

"The dates are very close, so this is probably the same person."
```

That behavior is unacceptable in a payment workflow.

#### Decision

The LLM only extracts identity information.

The actual verification is handled entirely by deterministic Python logic.

```text
User Input
    │
    ▼
LLM extracts DOB / PIN / Aadhaar
    │
    ▼
Deterministic validator
    │
    ├── Exact match → Verified
    │
    └── Mismatch   → Verification failure
```

#### Benefit

This guarantees:

* Exact identity matching
* Predictable behavior
* Controlled retry handling
* No probabilistic verification decisions
* Stronger security boundaries

---

### Decision 2 — Smart Routing Through Pydantic Field Descriptions

#### Problem

The account holder's name and the cardholder's name can be identical, but they represent different pieces of data and belong to different stages of the workflow.

For example:

```text
My name is Nithin Jain.
```

should normally populate:

```text
full_name
```

whereas:

```text
Cardholder name is Nithin Jain.
```

should populate:

```text
cardholder_name
```

Confusing these fields could cause the system to make incorrect assumptions about payment readiness.

#### Decision

Instead of implementing complicated Python-side "spillover" logic, the extraction schema uses explicit **Pydantic `Field` descriptions** to provide semantic routing instructions to the LLM.

Conceptually:

```python
full_name:
    Customer/account-holder name used during verification.

cardholder_name:
    Name printed on the payment card.
```

This gives the model explicit guidance about the purpose of each field.

#### Benefit

This approach:

* Keeps deterministic code simpler
* Reduces accidental field contamination
* Improves extraction accuracy
* Preserves a clean separation between verification and payment data

---

### Decision 3 — Security & Data Masking

Security requirements create an important tradeoff between **context richness** and **data exposure**.

The response-generation model does not require access to complete sensitive identifiers to produce an appropriate response.

Therefore, sensitive information is masked before the state is provided to the generation LLM.

Sensitive fields include:

```text
PIN
Aadhaar
Complete Date of Birth
Other sensitive identity information
```

The conceptual flow is:

```text
Verified ConversationState
          │
          ▼
    Safe State View
          │
      Mask PII
          │
          ▼
 Response Generation LLM
```

### Tradeoff

Masking slightly reduces the amount of contextual information available to the generation model.

However, this is intentionally accepted because **security is more important than giving the LLM unnecessary access to sensitive data**.

The model should know enough to explain the current state, but not enough to reproduce confidential identifiers.

---

## 4. Evaluation Strategy

Reliability is validated through an automated evaluation suite in `eval.py`.

Each evaluation scenario resets the agent state and tests a specific failure mode or edge case.

### Evaluation Matrix

| Scenario                   | What It Tests                                           |
| -------------------------- | ------------------------------------------------------- |
| Messy Human / Happy Path   | Multiple entities, natural phrasing, out-of-order input |
| Verification Lockout       | Retry counting and terminal state enforcement           |
| API Error Recovery         | Recovery from payment API failures                      |
| Leap Year Trap             | Correct date validation for Feb 29                      |
| Name Collision / Drip-Feed | Correct cardholder-name handling across multiple turns  |

### 4.1 Messy Human — Happy Path

Tests whether the agent can process a message containing several entities at once.

Example:

```text
ACC1001, Nithin Jain, PIN 400001, and I want to pay ₹500.
```

Expected behavior:

* Extract all entities
* Validate them
* Skip redundant questions
* Continue directly to the next missing payment fields

---

### 4.2 Verification Lockout

Tests the strict three-strike verification policy.

Expected behavior:

```text
Attempt 1 → Failure
Attempt 2 → Failure
Attempt 3 → Failure
                │
                ▼
        Terminal Lockout
```

Once the terminal state is reached, subsequent user input cannot restart verification within the same flow.

---

### 4.3 API Error Recovery

Simulates payment API failures such as:

```text
insufficient_balance
invalid_card
```

The agent should preserve valid information while isolating the invalid component.

For example:

```text
Valid:
- Amount
- CVV
- Expiry
- Cardholder Name

Invalid:
- Card Number
```

Only the card number should need correction.

This avoids unnecessary restarts and provides a more natural recovery experience.

---

### 4.4 Leap Year Validation

Explicitly tests date handling around February 29.

For example:

```text
2024-02-29  → Valid
2025-02-29  → Invalid
```

This ensures the deterministic date validator correctly follows calendar rules instead of relying on simple string-format validation.

---

### 4.5 Name Collision & Drip-Feed

This scenario validates two behaviors simultaneously:

1. Payment fields may arrive across multiple turns.
2. An explicitly supplied cardholder name overrides a previously inferred value.

Example:

```text
Card number: 4532015112830366
CVV: 123
Expiry: 12/27
```

followed later by:

```text
The name on the card is actually Raja B.
```

The agent must wait until all required payment fields are present and use the explicit cardholder name provided by the user.

---

## 5. Key Observations

### Pydantic Descriptions Have a Significant Impact on Extraction Quality

One of the most important observations from development was the relationship between **schema descriptions and LLM extraction quality**.

More precise field descriptions provided the model with clearer semantic boundaries.

For example, explicitly describing the intended meaning of:

```text
full_name
```

versus:

```text
cardholder_name
```

significantly improves routing behavior.

This reduced the need for complicated Python-side heuristics.

### Moving Natural-Language Normalization Into the LLM

Another useful observation was that some transformations are better handled during structured extraction.

Examples include:

```text
"five hundred"
→ 500

"twelve slash twenty-seven"
→ 12/27
```

Rather than implementing an increasing collection of regular expressions and normalization rules in Python, the extraction prompt can instruct the LLM to normalize common spoken representations into the required structured format.

This keeps the deterministic layer focused on what it does best:

> **Validation and enforcement rather than interpretation.**

---

## 6. Future Improvements

The current architecture is intentionally simple and deterministic, but several improvements would make it more suitable for production-scale deployment.

### 6.1 Asynchronous Architecture

The current implementation uses synchronous operations.

A production implementation could transition to:

```text
asyncio
+
aiohttp
```

This would allow LLM calls and external API interactions to execute asynchronously, reducing interface blocking and improving throughput under concurrent workloads.

Potential benefits include:

* Better responsiveness
* Higher concurrency
* More efficient I/O handling
* Improved scalability

---

### 6.2 Persistent Datastore

`ConversationState` currently lives in memory.

For a production deployment, the state should be stored in an external datastore such as:

```text
Redis
```

This would allow:

```text
User Session
     │
     ▼
Load State from Redis
     │
     ▼
Process Turn
     │
     ▼
Persist Updated State
```

Benefits include:

* Horizontal scaling
* Multi-instance deployments
* Session recovery
* Serverless compatibility
* Cross-request persistence

---

### 6.3 Model Optimization and Fine-Tuning

The current architecture relies on a general-purpose foundational model for structured extraction.

With sufficient historical conversation data, the extraction model could potentially be optimized for this specific domain.

Possible approaches include:

* Smaller task-specific models
* Fine-tuning
* Distillation
* Local inference
* Specialized extraction models

A smaller model could provide:

```text
Lower latency
+
Lower inference cost
+
Higher consistency for domain-specific extraction
```

while preserving the deterministic business layer as the final authority.

---

## 7. Security Boundary

The most important architectural principle is the **security boundary between probabilistic language understanding and deterministic execution**.

```text
┌────────────────────────────────────────────┐
│               LLM Responsibilities         │
│                                            │
│  • Understand natural language             │
│  • Extract entities                        │
│  • Resolve references                     │
│  • Normalize user input                    │
│  • Generate conversational responses       │
└───────────────────┬────────────────────────┘
                    │
                    │ Structured Data
                    ▼
┌────────────────────────────────────────────┐
│        Deterministic Responsibilities      │
│                                            │
│  • Validate data                           │
│  • Verify identity                         │
│  • Track retries                           │
│  • Enforce workflow state                  │
│  • Validate payment amounts                │
│  • Build API payloads                      │
│  • Trigger payment processing              │
│  • Enforce terminal states                 │
└────────────────────────────────────────────┘
```

This boundary is what allows the system to remain conversational without making financial execution probabilistic.

---

## 8. Conclusion

The AI Payment Collection Agent demonstrates how an LLM can be integrated into a security-sensitive workflow without allowing the model to control critical business decisions.

The architecture deliberately assigns different responsibilities to different layers:

* **LLM** → understands language
* **Pydantic schemas** → structure extracted information
* **Validators** → enforce correctness
* **ConversationState** → preserve trusted context
* **Agent** → control workflow transitions
* **API layer** → execute external operations
* **Generation LLM** → communicate the deterministic outcome naturally

The resulting architecture combines the flexibility of conversational AI with the predictability required for payment and identity workflows.

> **The LLM interprets. The state machine decides. The APIs execute.**
