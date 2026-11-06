# Asymptotic Space Complexity (Memory Analysis)

Analyze heap allocations, call stack frames, and auxiliary memory footprints across programming languages.

---

## 1. Input Space vs Auxiliary Space

- **Input Space**: The memory required to store the initial inputs given to the algorithm (e.g. an array of $n$ elements requires $O(n)$ input space).
- **Auxiliary Space**: The **extra or temporary memory** allocated by the algorithm exclusively during its execution (e.g. hash tables, temporary buffers, recursion frames).
- *Strict Rule*: When analyzing algorithmic space efficiency, evaluate **Auxiliary Space Complexity**.

---

## 2. In-Place vs Out-of-Place Algorithms

| Type | Definition | Auxiliary Space | Trade-offs |
|---|---|---|---|
| **In-Place** | Modifies input data structures directly without allocating auxiliary collections proportional to $n$. | **$O(1)$** | Highly memory-efficient; mutates caller data if not cloned; complex to parallelize. |
| **Out-of-Place** | Allocates new collections or copies to hold transformed data. | **$O(n)$** | Preserves input immutability; simplifies concurrent access; higher memory pressure and GC pauses. |

### Classic Comparison: In-Place Reverse vs Out-of-Place
```text
// In-Place (Two Pointers): Auxiliary Space = O(1)
function reverseInPlace(arr):
    left = 0, right = arr.length - 1
    while left < right:
        swap(arr[left], arr[right])
        left++, right--

// Out-of-Place: Auxiliary Space = O(n)
function reverseOutOfPlace(arr):
    new_arr = new Array(arr.length)
    for i from 0 to arr.length - 1:
        new_arr[i] = arr[arr.length - 1 - i]
    return new_arr
```

---

## 3. Recursion & Call Stack Frames

Every recursive invocation allocates a new **stack frame** storing local variables, parameters, and return addresses.

$$\text{Stack Space Complexity} = O(\text{Maximum Recursion Depth})$$

### The Recursion Trap
Even if an algorithm does not allocate a single array or object, deep recursion risks stack overflow if depth reaches $10^4$–$10^5$:

```text
// Time: O(n), Auxiliary Space: O(n) due to call stack depth!
function sumRecursive(n):
    if n <= 0: return 0
    return n + sumRecursive(n - 1)  // Allocates n stack frames!

// Time: O(n), Auxiliary Space: O(1)
function sumIterative(n):
    total = 0
    for i from 1 to n: total += i
    return total
```

---

## 4. Hidden Space Multipliers

### A. Substring & Slicing Copies
In languages where slicing or substring creates a copy (e.g. Python `arr[1:]` or Java pre-Java 7 `substring`), slicing inside a loop allocates quadratic memory:

```text
// ❌ ANTI-PATTERN: Allocates O(n^2) total memory across loop
while len(s) > 0:
    s = s[1:]  // Creates a new string copy of length n-1, n-2, ... -> O(n^2) memory!

// ✅ BEST PRACTICE: Use index pointers -> O(1) memory
start_idx = 0
while start_idx < len(s):
    start_idx += 1
```

### B. Intermediate Array Chains vs Streaming
Chaining array operations (`.filter().map().slice()`) allocates an intermediate array in memory for every step:

```text
// ❌ ANTI-PATTERN: Allocates 2 full intermediate arrays in RAM
const result = largeArray
  .filter(x => x % 2 === 0)   // Allocates array 1 (O(n))
  .map(x => x * 10);          // Allocates array 2 (O(n))

// ✅ BEST PRACTICE: Single pass accumulator or iterator/generator -> O(1) auxiliary
const result = [];
for (const x of largeArray) {
  if (x % 2 === 0) result.push(x * 10);
}
```
