# Asymptotic Time Complexity (Big-O Analysis)

Mathematical foundations and rules for calculating, ranking, and auditing time complexity across all programming languages.

---

## 1. Asymptotic Notations

| Notation | Formal Definition | Engineering Meaning | When to Use in Audits |
|---|---|---|---|
| **Big-O ($O$)** | $f(n) \le c \cdot g(n)$ for $n \ge n_0$ | **Upper Bound** (Worst-Case Guarantee) | Standard for performance guarantees & SLA contracts. |
| **Big-Omega ($\Omega$)** | $f(n) \ge c \cdot g(n)$ for $n \ge n_0$ | **Lower Bound** (Best-Case Limit) | Proving theoretical minimum steps required. |
| **Big-Theta ($\Theta$)** | $c_1 g(n) \le f(n) \le c_2 g(n)$ | **Tight Bound** (Matches both upper & lower) | Accurate description of algorithms whose best & worst cases match. |

---

## 2. Big-O Complexity Ranking Hierarchy

From fastest to slowest:

$$O(1) < O(\log n) < O(\sqrt{n}) < O(n) < O(n \log n) < O(n^2) < O(n^3) < O(2^n) < O(n!)$$

| Complexity Class | Growth Rate with $n=10^6$ | Common Real-World Examples | Production Viability |
|---|---|---|---|
| **$O(1)$** (Constant) | 1 operation | Hash table lookup, array indexing, math formulas, bit shifts. | Optimal for real-time APIs. |
| **$O(\log n)$** (Logarithmic) | $\approx 20$ operations | Binary search, balanced BST operations (AVL, Red-Black), bisect. | Excellent for massive datasets. |
| **$O(n)$** (Linear) | $10^6$ operations | Single-pass scan, finding min/max, linear search, accumulator. | Baseline standard for unindexed streams. |
| **$O(n \log n)$** (Linearithmic) | $\approx 2 \times 10^7$ operations | Efficient sorting (Timsort, MergeSort, QuickSort avg, HeapSort). | Maximum acceptable for bulk sorting. |
| **$O(n^2)$** (Quadratic) | $10^{12}$ operations (Timeout/Crash!) | Nested loops over same collection, pairwise checks, naive bubble sort. | Unacceptable for $n > 5,000$. |
| **$O(n^3)$** (Cubic) | $10^{18}$ operations | 3 nested loops, naive matrix multiplication, all-pairs triplets. | Unacceptable for $n > 500$. |
| **$O(2^n)$** (Exponential) | Incalculable | Naive recursion without memoization (Fibonacci, subsets, knapsack). | Only feasible for $n < 30$. |
| **$O(n!)$** (Factorial) | Incalculable | Generating all permutations, brute-force traveling salesman. | Only feasible for $n \le 12$. |

---

## 3. Mathematical Rules for Calculating Time Complexity

### A. Dropping Non-Dominant Terms & Constant Factors
Always retain only the highest-order term and drop constant multipliers:

$$O(5n^3 + 120n^2 + 10^6) \implies O(n^3)$$

$$O(100n) \implies O(n)$$

*(Note: While constant factors are dropped in Big-O analysis, in high-frequency trading or embedded systems, a $3n$ algorithm is 3x faster than a $9n$ algorithm).*

### B. Product Rule (Nested Operations)
When an inner block runs $m$ times for every iteration of an outer loop that runs $n$ times:

$$\text{Complexity} = O(n \cdot m)$$

```text
for i in 0..n:
    for j in 0..m:
        do_constant_work()  // O(n * m). If n == m, this is O(n^2)
```

### C. Sum Rule (Sequential Operations)
When independent blocks execute sequentially, the total complexity is the maximum of the blocks:

$$\text{Total} = O(f(n) + g(n)) = \max(O(f(n)), O(g(n)))$$

```text
for i in 0..n: ...       // O(n)
for j in 0..n:
    for k in 0..n: ...   // O(n^2)
// Total Complexity = O(n + n^2) = O(n^2)
```

### D. Logarithmic Loop Progression
Whenever a loop variable is **multiplied or divided** by a constant factor on each step, the loop is logarithmic:

```text
i = 1
while i < n:
    i = i * 2  // Executes ceil(log2(n)) times -> O(log n)
```

---

## 4. Amortized Time Complexity

An operation has **Amortized Time Complexity** $O(1)$ if an occasional expensive operation (costing $O(n)$) happens so infrequently that the average cost per operation across a long sequence of $N$ operations remains constant.

### Classic Examples:
1. **Dynamic Array Resizing (`vector.push_back`, `list.append`, `array.push`)**:
   - Most appends take $O(1)$ (insert into pre-allocated buffer).
   - When capacity is reached, it allocates a new buffer of size $2N$ and copies elements ($O(N)$).
   - Across $N$ appends, total copy operations $\le 2N$, resulting in **amortized $O(1)$**.
2. **Hash Table Rehashing**:
   - When load factor threshold is breached, a new bucket array is allocated and all keys re-hashed ($O(n)$). Amortized cost per insertion remains $O(1)$.

