# Page Object Model & Resilient Locators

Design maintainable Page Object Models (POM) and use accessible Playwright locators that never break on CSS redesigns.

---

## 1. Separation of Responsibilities in BDD

```
┌─────────────────────────────────┐
│ Gherkin Feature (.feature)      │  -> Business requirements in human language
└────────────────┬────────────────┘
                 │ calls
┌────────────────▼────────────────┐
│ Step Definitions (.steps.ts)   │  -> Test orchestration & assertion boundaries
└────────────────┬────────────────┘
                 │ calls
┌────────────────▼────────────────┐
│ Page Object Models (.ts)        │  -> Encapsulates DOM locators & browser actions
└────────────────┬────────────────┘
                 │ drives
┌────────────────▼────────────────┐
│ Playwright Browser Engine       │  -> Executes Chromium/Firefox/WebKit actions
└─────────────────────────────────┘
```

---

## 2. Playwright Locator Priority Hierarchy

Always select locators matching how real users interact with the page (accessibility tree) rather than fragile DOM implementation details:

| Rank | Locator Method | Purpose | Resilient? |
|---|---|---|---|
| **1 (Best)** | `page.getByRole('button', { name: 'Sign in' })` | Accessible ARIA role & accessible name. | ✅ Highest (immune to CSS/tag changes) |
| **2** | `page.getByLabel('Email address')` | Associated `<label>` elements for inputs. | ✅ High |
| **3** | `page.getByPlaceholder('Search products...')` | Input placeholder text. | ✅ Good |
| **4** | `page.getByText('Order Confirmation')` | Exact visible non-interactive text. | ✅ Good |
| **5** | `page.getByTestId('cart-total')` | Explicit `data-testid` attribute. | ✅ Reliable fallback for dynamic custom UI |
| **6 (Avoid)** | `page.locator('.btn-primary')` | CSS classes. | ❌ Brittle (breaks on CSS redesigns) |
| **7 (Ban)** | `page.locator('//div[3]/ul/li[2]/a')` | Deep positional XPath. | ❌ Extremely fragile |

---

## 3. Reference Page Object Implementation

```typescript
// tests/pages/CheckoutPage.ts
import { type Page, type Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class CheckoutPage extends BasePage {
  // 1. Expose locators as readonly properties using resilient selectors
  readonly totalAmount: Locator;
  readonly shippingAddressInput: Locator;
  readonly standardShippingRadio: Locator;
  readonly placeOrderButton: Locator;
  readonly confirmationModal: Locator;

  constructor(page: Page) {
    super(page);
    this.totalAmount = page.getByTestId('total-billed-amount');
    this.shippingAddressInput = page.getByLabel('Shipping Address');
    this.standardShippingRadio = page.getByRole('radio', { name: 'Standard Shipping' });
    this.placeOrderButton = page.getByRole('button', { name: 'Place Order' });
    this.confirmationModal = page.getByRole('dialog', { name: 'Order Placed' });
  }

  // 2. High-level action methods
  async enterShippingDetails(address: string): Promise<void> {
    await this.shippingAddressInput.fill(address);
    await this.standardShippingRadio.check();
  }

  async submitOrder(): Promise<void> {
    await this.placeOrderButton.click();
  }
}
```

---

## 4. Java Page Object Pattern (Playwright Java)

```java
// src/test/java/com/example/bdd/pages/CheckoutPage.java
package com.example.bdd.pages;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;

public class CheckoutPage {
    private final Page page;
    public final Locator totalAmount;
    public final Locator shippingAddressInput;
    public final Locator standardShippingRadio;
    public final Locator placeOrderButton;

    public CheckoutPage(Page page) {
        this.page = page;
        this.totalAmount = page.getByTestId("total-billed-amount");
        this.shippingAddressInput = page.getByLabel("Shipping Address");
        this.standardShippingRadio = page.getByRole(AriaRole.RADIO, new Page.GetByRoleOptions().setName("Standard Shipping"));
        this.placeOrderButton = page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Place Order"));
    }

    public void enterShippingDetails(String address) {
        shippingAddressInput.fill(address);
        standardShippingRadio.check();
    }

    public void submitOrder() {
        placeOrderButton.click();
    }
}
```

---

## 5. C# Page Object Pattern (Playwright .NET)

```csharp
// Pages/CheckoutPage.cs
using System.Threading.Tasks;
using Microsoft.Playwright;

namespace MyBddTests.Pages
{
    public class CheckoutPage
    {
        private readonly IPage _page;
        public ILocator TotalAmount { get; }
        public ILocator ShippingAddressInput { get; }
        public ILocator StandardShippingRadio { get; }
        public ILocator PlaceOrderButton { get; }

        public CheckoutPage(IPage page)
        {
            _page = page;
            TotalAmount = page.GetByTestId("total-billed-amount");
            ShippingAddressInput = page.GetByLabel("Shipping Address");
            StandardShippingRadio = page.GetByRole(AriaRole.Radio, new() { Name = "Standard Shipping" });
            PlaceOrderButton = page.GetByRole(AriaRole.Button, new() { Name = "Place Order" });
        }

        public async Task EnterShippingDetailsAsync(string address)
        {
            await ShippingAddressInput.FillAsync(address);
            await StandardShippingRadio.CheckAsync();
        }

        public async Task SubmitOrderAsync()
        {
            await PlaceOrderButton.ClickAsync();
        }
    }
}
```

