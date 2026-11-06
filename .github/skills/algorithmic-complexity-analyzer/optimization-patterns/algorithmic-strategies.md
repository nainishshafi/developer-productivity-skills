# Algorithmic Optimization Strategies

Standard patterns for transforming algorithms into superior Big-O complexity classes.

---

## 1. Hash Map Inversion ($O(n^2) \to O(n)$)

### The Pattern
When an algorithm searches for complementary pairs or pairs satisfying a condition (e.g. Two-Sum, finding duplicates, joining datasets), replace the inner loop with a Hash Map lookup.

```text
// ❌ Naive Brute-Force: O(n^2)
for i from 0 to n:
    for j from i+1 to n:
        if arr[i] + arr[j] == target:
            return [i, j]

// ✅ Hash Map Inversion: O(n) Time, O(n) Auxiliary Space
seen = new Map()
for i from 0 to n:
    complement = target - arr[i]
    if seen.has(complement):
        return [seen.get(complement), i]
    seen.set(arr[i], i)
```

---

## 2. Two-Pointer Technique ($O(n^2) \to O(n)$)

### The Pattern
When operating on a sorted array or sequence, use two index pointers moving toward each other or in parallel to avoid nested iterations.

```text
// Find if pair sums to target in a SORTED array:
left = 0, right = n - 1
while left < right:
    current_sum = arr[left] + arr[right]
    if current_sum == target:
        return true
    else if current_sum < target:
        left++   // Need larger sum
    else:
        right--  // Need smaller sum
// Time Complexity: O(n), Auxiliary Space: O(1)
```

---

## 3. Sliding Window ($O(n \cdot k) \to O(n)$)

### The Pattern
When computing contiguous subarray aggregates (e.g. max sum of subarray of size $k$, longest substring without repeating characters), instead of recomputing the entire window of size $k$ from scratch on every step, update the aggregate by adding the incoming element and subtracting the outgoing element.

```text
// ❌ Naive: O(n * k)
for i from 0 to n - k:
    sum = 0
    for j from i to i + k: sum += arr[j]

// ✅ Sliding Window: O(n)
window_sum = sum of first k elements
max_sum = window_sum
for i from k to n:
    window_sum += arr[i] - arr[i - k] // O(1) update!
    max_sum = max(max_sum, window_sum)
```

---

## 4. Binary Search / Bisection ($O(n) \to O(\log n)$)

### The Pattern
Whenever the search space is monotonic (sorted values, or answer space where values $\le x$ are valid and $> x$ are invalid), bisect the range by half on each iteration instead of testing values linearly.

```text
low = 0, high = n - 1
while low <= high:
    mid = low + ((high - low) / 2) // Avoids integer overflow
    if arr[mid] == target: return mid
    else if arr[mid] < target: low = mid + 1
    else: high = mid - 1
```

---

## 5. Memoization & Dynamic Programming ($O(2^n) \to O(n)$)

### The Pattern
Identify overlapping subproblems and optimal substructure. Cache subproblem solutions (Top-Down with memo table or Bottom-Up tabular DP) to avoid recalculating the same branch.

```text
// Top-Down Memoized Fibonacci:
memo = new Map()
function fib(n):
    if n <= 1: return n
    if memo.has(n): return memo.get(n)
    result = fib(n - 1) + fib(n - 2)
    memo.set(n, result)
    return result
// Time: O(n), Space: O(n)
```
