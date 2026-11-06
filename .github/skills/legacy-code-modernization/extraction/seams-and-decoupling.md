# Seams, Dependency Breaking & Code Extraction

Techniques for safely breaking dependencies, isolating code, and extracting units from legacy codebases based on Michael Feathers' *Working Effectively with Legacy Code*.

---

## 1. What is a Seam?

> **Definition:** A **Seam** is a place in a codebase where you can alter behavior without editing code in that place. Every seam has an enabling point where you choose which behavior to execute.

### Common Seam Types:
1. **Object Seams**: In object-oriented languages, passing an interface or base class into a constructor or method allows swapping a production dependency for a test double.
2. **Link Seams**: Swapping modules or libraries at build/import time (e.g. mocking an imported module in Python/JavaScript).
3. **Functional Seams**: Passing functions or closures as parameters rather than hardcoding static function calls.

---

## 2. The 4 Essential Dependency-Breaking Techniques

### Technique 1: Parameterize Constructor (Injecting Hidden Dependencies)
Legacy code often instantiates heavy resources (database clients, HTTP sockets, system clocks) directly inside constructors or methods.

```typescript
// ❌ UNTESTABLE LEGACY CODE: Hardcoded instantiation inside class
export class OrderProcessor {
  private db: DatabaseClient;
  private paymentGateway: StripeGateway;

  constructor() {
    this.db = new DatabaseClient('prod-db-connection-string'); // Can't test without real DB!
    this.paymentGateway = new StripeGateway(process.env.STRIPE_KEY!);
  }
}

// ✅ EXTRACTED SEAM: Parameterize Constructor with Default Fallbacks
export class OrderProcessor {
  constructor(
    private db: DatabaseClient = new DatabaseClient(process.env.DATABASE_URL!),
    private paymentGateway: PaymentGatewayPort = new StripeGateway(process.env.STRIPE_KEY!)
  ) {}
}
```
*Effect:* Production code continues calling `new OrderProcessor()` unchanged, but tests can inject in-memory fakes.

---

### Technique 2: Extract Interface / Port
When a legacy class directly depends on a concrete third-party or infrastructure class:

```python
# ❌ LEGACY: Directly coupled to concrete SendGrid client
class NotificationService:
    def __init__(self):
        self.client = SendGridAPIClient(os.environ["SENDGRID_KEY"])

    def send_alert(self, email: str, msg: str):
        self.client.mail.send(to=email, content=msg)

# ✅ EXTRACTED SEAM: Introduce a Protocol/Interface Port
from typing import Protocol

class EmailSenderPort(Protocol):
    def send(self, to: str, content: str) -> None: ...

class NotificationService:
    def __init__(self, sender: EmailSenderPort):
        self.sender = sender

    def send_alert(self, email: str, msg: str):
        self.sender.send(to=email, content=msg)
```

---

### Technique 3: Subclass and Override Method
When a legacy class cannot be easily refactored because a private/protected method calls an unmockable static method or OS resource:

```java
// Legacy class with untestable side effect
public class LegacyBillingService {
    public void processInvoice(Invoice inv) {
        // ... business calculation ...
        sendAuditLogToRemoteSyslog(inv); // Blocks testing if syslog server is unreachable!
    }

    protected void sendAuditLogToRemoteSyslog(Invoice inv) {
        SyslogSocket.sendRawPacket(inv.toString());
    }
}

// In Test: Subclass and Override the seam
public class TestableBillingService extends LegacyBillingService {
    public boolean auditSent = false;

    @Override
    protected void sendAuditLogToRemoteSyslog(Invoice inv) {
        this.auditSent = true; // Overridden seam! Zero network traffic
    }
}
```

---

### Technique 4: Sprout Class / Sprout Method
When adding new functionality to a 3,000-line legacy method:
- **Do NOT** add another 50 lines to the giant method.
- **Sprout a new class** or standalone pure function containing the new logic.
- Call the sprouted component from the legacy method. Write 100% TDD unit tests for the sprouted component.

