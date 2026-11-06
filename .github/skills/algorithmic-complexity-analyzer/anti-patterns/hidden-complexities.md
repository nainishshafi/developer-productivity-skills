# Hidden Complexity Anti-Patterns & Bottlenecks

Common programming traps that disguise exponential or quadratic algorithms as innocent linear code.

---

## 1. The "Hidden Loop" Trap ($O(n) \to O(n^2)$)

Calling a collection membership check or linear search inside an outer loop converts an innocent single-pass loop into a quadratic $O(n^2)$ bottleneck.

### Language-Specific Manifestations

| Language | The Innocent-Looking Expression | Hidden Cost per Iteration | Total Result |
|---|---|---|---|
| **Python** | `if item in my_list:` | $O(n)$ linear scan | $O(n^2)$ |
| **JavaScript / TypeScript** | `array.includes(item)` or `array.indexOf(item) !== -1` | $O(n)$ linear scan | $O(n^2)$ |
| **Java** | `arrayList.contains(item)` | $O(n)$ linear scan | $O(n^2)$ |
| **C#** | `list.Contains(item)` | $O(n)$ linear scan | $O(n^2)$ |
| **Go** | `slices.Contains(slice, item)` | $O(n)$ linear scan | $O(n^2)$ |

### Code Comparison
```python
# ❌ ANTI-PATTERN: O(n * m) -> O(n^2) when n == m
# For 100,000 items, this performs 10,000,000,000 equality checks!
def find_common_bad(list_a, list_b):
    common = []
    for item in list_a:          # Loops n times
        if item in list_b:       # Hidden inner loop: scans m elements -> O(m)
            common.append(item)
    return common

# ✅ OPTIMIZED: Pre-index into HashSet -> Total O(n + m)
# For 100,000 items, this performs only 200,000 operations!
def find_common_good(list_a, list_b):
    set_b = set(list_b)          # O(m) one-time hash set construction
    return [item for item in list_a if item in set_b]  # O(1) hash lookup per item -> O(n)
```

---

## 2. Array Shift / Queue Pop-From-Front ($O(n) \to O(n^2)$)

Using a standard contiguous array or list as a FIFO (First-In, First-Out) queue by repeatedly removing from index 0 forces the runtime to re-index and shift all remaining $n - 1$ elements in memory on every dequeue.

```typescript
// ❌ ANTI-PATTERN: O(n^2) Queue Drain
// array.shift() shifts n elements in memory every single iteration
function processQueueBad(queue: Task[]) {
  while (queue.length > 0) {
    const task = queue.shift();  // O(n) operation per item!
    task.execute();
  }
}

// ✅ OPTIMIZED: Use an index pointer or a true Deque -> O(n) total
function processQueueGood(queue: Task[]) {
  let head = 0;
  while (head < queue.length) {
    const task = queue[head++];  // O(1) direct index lookup
    task.execute();
  }
  queue.length = 0; // Clear memory after processing
}
```

---

## 3. String Concatenation in Loops ($O(n) \to O(n^2)$)

In most languages (Java, Python, C#, JavaScript), strings are **immutable**. Concatenating with `+=` inside a loop creates a completely new string object and copies all previous characters into it on every iteration.

$$\text{Total Copies} = 1 + 2 + 3 + \dots + n = \frac{n(n + 1)}{2} = O(n^2)$$

```java
// ❌ ANTI-PATTERN: O(n^2) String Copying
String result = "";
for (String word : words) {
    result += word + ","; // Allocates new string and copies all previous chars every loop!
}

// ✅ OPTIMIZED: Bounded StringBuilder / Array Join -> O(n)
StringBuilder sb = new StringBuilder(estimatedCapacity);
for (String word : words) {
    sb.append(word).append(",");
}
String result = sb.toString();
```

---

## 4. Unmemoized Recursive Branching ($O(2^n)$ Explosion)

Recursive functions that make 2 or more recursive calls without caching intermediate results re-compute the same subproblems millions of times:

```text
Fibonacci Tree:
                  fib(5)
              /            \
          fib(4)          fib(3)
         /      \        /      \
      fib(3)  fib(2)   fib(2)  fib(1)
      ... repeated identical work!
```

$$\text{Unmemoized Time Complexity} = O(2^n) \quad (\text{For } n=50, 2^{50} \approx 10^{15} \text{ steps})$$

$$\text{Memoized / DP Time Complexity} = O(n) \quad (\text{For } n=50, 50 \text{ steps})$$

