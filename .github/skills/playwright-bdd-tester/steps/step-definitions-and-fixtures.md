# Step Definitions, Expressions & Fixture Injection

Map Gherkin steps to executable Playwright automation using parameter expressions and custom fixtures.

---

## 1. Writing Step Definitions (`playwright-bdd` / TypeScript)

Use `createBdd()` to obtain typed `Given`, `When`, and `Then` functions that receive Playwright fixtures:

```typescript
// tests/steps/checkout.steps.ts
import { expect } from '@playwright/test';
import { createBdd } from 'playwright-bdd';
import { test } from '../fixtures/testFixtures';

const { Given, When, Then } = createBdd(test);

// 1. Given step with {string} parameter
Given('the user {string} is signed in', async ({ loginPage }, email: string) => {
  await loginPage.navigate();
  await loginPage.login(email, 'validPassword123');
});

// 2. Given step with DataTable
Given('the catalog contains:', async ({ catalogPage }, dataTable) => {
  // dataTable.hashes() returns array of { product: string, price: string, in_stock: string }
  for (const row of dataTable.hashes()) {
    await catalogPage.verifyItemAvailable(row.product, parseFloat(row.price));
  }
});

// 3. When step with string parameter
When('the user adds {string} to their cart', async ({ catalogPage }, productName: string) => {
  await catalogPage.addToCart(productName);
});

// 4. Then step with web-first assertions
Then('the total billed amount should be {string}', async ({ checkoutPage }, expectedTotal: string) => {
  // Web-first assertion with auto-retry
  await expect(checkoutPage.totalAmount).toHaveText(expectedTotal);
});
```

---

## 2. Parameter Expressions & Types

| Expression | Matches | Example Match | Typed Argument |
|---|---|---|---|
| `{string}` | Text enclosed in double or single quotes | `"alice@test.com"`, `'Desk'` | `string` |
| `{int}` | Signed integer | `42`, `-5` | `number` |
| `{float}` | Signed floating-point number | `49.99`, `-0.5` | `number` |
| `{word}` | A single word without whitespace | `admin`, `standard` | `string` |
| `{}` | Anonymous parameter (any text) | `any unquoted string` | `string` |

---

## 3. Custom Fixture Injection (Eliminating `new Page()` Boilerplate)

Never instantiate Page Objects manually inside step definitions. Inject them as Playwright fixtures so Playwright manages page lifecycle, storage state, and isolation:

```typescript
// tests/fixtures/testFixtures.ts
import { test as base } from 'playwright-bdd';
import { LoginPage } from '../pages/LoginPage';
import { CatalogPage } from '../pages/CatalogPage';
import { CheckoutPage } from '../pages/CheckoutPage';

type CustomPages = {
  loginPage: LoginPage;
  catalogPage: CatalogPage;
  checkoutPage: CheckoutPage;
};

export const test = base.extend<CustomPages>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  catalogPage: async ({ page }, use) => {
    await use(new CatalogPage(page));
  },
  checkoutPage: async ({ page }, use) => {
    await use(new CheckoutPage(page));
  },
});
```

---

## 4. Python Step Definitions (`pytest-bdd`)

```python
# tests/steps/checkout_steps.py
from pytest_bdd import given, when, then, parsers
from playwright.sync_api import Page, expect

@given(parsers.parse('the user "{email}" is signed in'))
def user_signed_in(page: Page, email: str):
    page.goto("/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill("validPassword123")
    page.get_by_role("button", name="Sign in").click()

@then(parsers.parse('the total billed amount should be "{expected_total}"'))
def verify_total(page: Page, expected_total: str):
    total_locator = page.get_by_test_id("total-amount")
    expect(total_locator).to_have_text(expected_total)
```

---

## 5. Java Step Definitions (Cucumber-JVM + Playwright)

```java
// src/test/java/com/example/bdd/steps/CheckoutSteps.java
package com.example.bdd.steps;

import com.microsoft.playwright.Page;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class CheckoutSteps {
    private final Page page;

    // Injected via Cucumber PicoContainer or DI framework
    public CheckoutSteps(TestContext context) {
        this.page = context.getPage();
    }

    @Given("the user {string} is signed in")
    public void userIsSignedIn(String email) {
        page.navigate("/login");
        page.getByLabel("Email").fill(email);
        page.getByLabel("Password").fill("validPassword123");
        page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Sign in")).click();
    }

    @Then("the total billed amount should be {string}")
    public void totalBilledShouldBe(String expectedTotal) {
        assertThat(page.getByTestId("total-amount")).hasText(expectedTotal);
    }
}
```

---

## 6. C# Step Definitions (Reqnroll / SpecFlow + Playwright .NET)

```csharp
// Steps/CheckoutSteps.cs
using System.Threading.Tasks;
using Microsoft.Playwright;
using Reqnroll;
using static Microsoft.Playwright.Assertions;

namespace MyBddTests.Steps
{
    [Binding]
    public class CheckoutSteps
    {
        private readonly IPage _page;

        public CheckoutSteps(ScenarioContext context)
        {
            _page = context.Get<IPage>();
        }

        [Given(@"the user ""(.*)"" is signed in")]
        public async Task GivenTheUserIsSignedIn(string email)
        {
            await _page.GotoAsync("/login");
            await _page.GetByLabel("Email").FillAsync(email);
            await _page.GetByLabel("Password").FillAsync("validPassword123");
            await _page.GetByRole(AriaRole.Button, new() { Name = "Sign in" }).ClickAsync();
        }

        [Then(@"the total billed amount should be ""(.*)""")]
        public async Task ThenTheTotalAmountShouldBe(string expectedTotal)
        {
            await Expect(_page.GetByTestId("total-amount")).ToHaveTextAsync(expectedTotal);
        }
    }
}
```

