# TypeScript Domain Modeling & Type Discipline

Make illegal states unrepresentable through strict typing, discriminated unions, and domain boundary separation.

---

## 1. Discriminated Unions (State Variants)

Never use optional properties and boolean flags to model mutually exclusive state. Use discriminated unions:

```typescript
// ❌ ANTI-PATTERN: Ambiguous states, impossible combinations allowed
interface Payment {
  id: string;
  isPending: boolean;
  isAuthorized: boolean;
  isFailed: boolean;
  authCode?: string;      // When is this defined?
  failureReason?: string; // Can this exist if isAuthorized is true?
}

// ✅ BEST PRACTICE: Discriminated union enforces valid state combinations
export type Payment =
  | { status: 'PENDING'; id: string; createdAt: Date }
  | { status: 'AUTHORIZED'; id: string; authCode: string; authorizedAt: Date }
  | { status: 'FAILED'; id: string; failureReason: string; failedAt: Date };

function processPayment(payment: Payment) {
  switch (payment.status) {
    case 'PENDING':
      return initiateCharge(payment.id);
    case 'AUTHORIZED':
      return captureCharge(payment.id, payment.authCode);
    case 'FAILED':
      return notifyFailure(payment.id, payment.failureReason);
  }
}
```

---

## 2. Branded / Nominal Types

TypeScript uses structural typing. When two primitives have different business meanings (e.g., `UserId` vs `OrderId`), use branded types to prevent accidental swapping:

```typescript
declare const brand: unique symbol;

export type Branded<T, BrandTag extends string> = T & { readonly [brand]: BrandTag };

export type UserId = Branded<string, 'UserId'>;
export type OrderId = Branded<string, 'OrderId'>;

export function makeUserId(raw: string): UserId {
  return raw as UserId;
}

export function makeOrderId(raw: string): OrderId {
  return raw as OrderId;
}

function cancelOrder(userId: UserId, orderId: OrderId) { ... }

// Compiler flags accidental inversion:
// cancelOrder(orderId, userId); // Error: Type '"OrderId"' is not assignable to type '"UserId"'
```

---

## 3. Separating Domain Types from API DTOs

Never expose internal database entities or domain aggregate types directly over public HTTP interfaces:

```typescript
// Domain Entity (Pure, internal invariants)
export interface UserEntity {
  id: UserId;
  email: string;
  hashedPassword: string; // Internal secret!
  role: 'ADMIN' | 'MEMBER';
  createdAt: Date;
}

// Public API DTO (Sanitized, explicitly contracted)
export interface UserResponseDto {
  id: string;
  email: string;
  role: 'ADMIN' | 'MEMBER';
}

export function toUserResponseDto(user: UserEntity): UserResponseDto {
  return {
    id: user.id,
    email: user.email,
    role: user.role,
  };
}
```

---

## 4. `as const` and Literal Constants

```typescript
export const ORDER_STATUS = {
  DRAFT: 'DRAFT',
  SUBMITTED: 'SUBMITTED',
  FULFILLED: 'FULFILLED',
} as const;

export type OrderStatus = (typeof ORDER_STATUS)[keyof typeof ORDER_STATUS];
```

