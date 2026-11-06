# Gherkin Syntax, BDD Principles & Scenario Design

Standards for writing human-readable, maintainable Gherkin feature files that bridge business requirements with automated Playwright browser tests.

---

## 1. Gherkin Structural Components

A `.feature` file organizes executable specifications using strict keywords:

| Keyword | Purpose | Example |
|---|---|---|
| **`Feature:`** | High-level title and description of a business capability. | `Feature: Shopping Cart & Checkout` |
| **`Rule:`** | (Gherkin v6+) Represents a specific business rule containing scenarios. | `Rule: Free shipping applies on orders over $50` |
| **`Background:`** | Steps run before *every* scenario in this feature file. | `Given the user is logged in as "Standard Customer"` |
| **`Scenario:`** | A concrete user journey testing one behavior. | `Scenario: Add in-stock product to cart` |
| **`Scenario Outline:`** | Parameterized scenario executed across a table of examples. | `Scenario Outline: Login with invalid credentials` |
| **`Examples:`** | Data table supplying values to a `Scenario Outline`. | Table of `| username | password | error |` |
| **`Given`** | Sets up the initial context and preconditions. | `Given the product "Wireless Mouse" has 5 units in stock` |
| **`When`** | The action or event triggered by the actor. | `When the user adds "Wireless Mouse" to their cart` |
| **`Then`** | The observable outcome or assertion. | `Then the cart total should display "$29.99"` |
| **`And` / `But`** | Conjunctions extending previous Given/When/Then steps. | `And the cart badge should show "1"` |
| **`@tags`** | Labels used for test filtering in CI (`@smoke`, `@auth`, `@regression`). | `@smoke @checkout` |

---

## 2. Declarative vs Imperative Scenarios (The #1 BDD Pitfall)

Never write Gherkin scenarios like manual QA click scripts with button clicks, CSS selectors, and keystroke details. Write **declarative** scenarios focused on business intent.

### ❌ Anti-Pattern: Imperative (Coupled to UI implementation, unreadable by stakeholders)
```gherkin
Scenario: Checkout item
  Given user opens browser and navigates to "https://app.com/login"
  When user types "alice@test.com" into input "#email"
  And user types "secret123" into input "#pass"
  And user clicks button "button[type='submit']"
  And user waits 2 seconds
  And user clicks div ".product-card:nth-child(1)"
  And user clicks button "#add-to-cart-btn"
  And user navigates to "/checkout"
  Then div ".total" should have text "$49.00"
```

### ✅ Best Practice: Declarative (Expresses business rules; UI details live in Page Objects)
```gherkin
@smoke @checkout
Feature: Order Checkout

  Background:
    Given the user "alice@test.com" is signed in
    And the catalog contains:
      | product       | price | in_stock |
      | Ergonomic Desk | 49.00 | true     |

  Scenario: Successfully checkout with standard shipping
    When the user adds "Ergonomic Desk" to their cart
    And completes checkout with standard shipping
    Then the order confirmation screen should display
    And the total billed amount should be "$49.00"
```

---

## 3. DataTables & Parameter Tables

Use DataTables to pass structured rows into step definitions cleanly:

```gherkin
Scenario: Bulk inventory update
  When the administrator updates inventory thresholds:
    | sku      | min_threshold | max_threshold | reorder_point |
    | DSK-1001 | 5             | 50            | 10            |
    | CHR-2002 | 10            | 100           | 20            |
  Then the stock alert notifications should be recalibrated
```

---

## 4. Scenario Outline for Boundary Value Testing

```gherkin
Scenario Outline: Password complexity validation
  When a new user registers with password "<password>"
  Then registration should fail with error "<error_message>"

  Examples:
    | password    | error_message                                 |
    | short       | Password must be at least 8 characters        |
    | alllowercase | Password must contain at least one uppercase letter |
    | 12345678    | Password must contain at least one special character |
```
