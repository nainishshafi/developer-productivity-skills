# Empirical Asymptotic Benchmarking via MCP (`nodejs-executor`)

A rigorous protocol for validating theoretical Big-O complexity predictions through empirical runtime and heap measurements using the `nodejs-executor` MCP server.

---

## 1. The Doubling Hypothesis Ratio Test

Theoretical analysis can sometimes overlook engine optimizations (JIT inlining, branch prediction) or hidden language costs (dynamic array reallocations, hidden hash collisions). The **Doubling Hypothesis** validates the asymptotic order of growth by measuring execution time $T(n)$ as input size $N$ doubles ($N \to 2N$):

$$\text{Growth Ratio } R = \lim_{N \to \infty} \frac{T(2N)}{T(N)}$$

### Asymptotic Growth Ratio Reference

| Theoretical Bound | Complexity Class | Expected Ratio $R = \frac{T(2N)}{T(N)}$ | Behavior as $N$ Doubles |
|---|---|---|---|
| $O(1)$ | Constant | $\approx 1.0$ | Execution time is invariant to input size. |
| $O(\log n)$ | Logarithmic | $\approx 1.0$ | Negligible change ($\frac{\log(2N)}{\log N} \to 1$). |
| $O(n)$ | Linear | $\approx 2.0$ | Time doubles when input doubles. |
| $O(n \log n)$ | Linearithmic | $\approx 2.1 - 2.3$ | Slightly more than double due to the logarithmic term. |
| $O(n^2)$ | Quadratic | $\approx 4.0$ | Time quadruples ($2^2$) when input doubles. |
| $O(n^3)$ | Cubic | $\approx 8.0$ | Time multiplies by 8 ($2^3$) when input doubles. |
| $O(2^n)$ | Exponential | $> 100 \times$ (Explodes) | $T(N+1)/T(N) \approx 2.0$; doubling $N$ freezes the process. |

---

## 2. Invoking Empirical Benchmarks via MCP

When connected to the **`nodejs-executor`** MCP server in Claude Code, Cursor, Copilot, or Antigravity, use `execute_code` with `sandboxMode: "strict"`.

### MCP Tool Payload Template

```json
{
  "name": "execute_code",
  "arguments": {
    "language": "javascript",
    "sandboxMode": "strict",
    "code": "const Ns = [500, 1000, 2000, 4000, 8000];\n\nfunction targetAlgorithm(arr) {\n  let count = 0;\n  for (let i = 0; i < arr.length; i++) {\n    if (arr.includes(i)) count++; // Hidden O(n^2) trap\n  }\n  return count;\n}\n\n// Warmup JIT\ntargetAlgorithm([1, 2, 3]);\n\nconst results = [];\nlet prevTime = null;\n\nfor (const n of Ns) {\n  const input = Array.from({ length: n }, (_, i) => i);\n  const t0 = performance.now();\n  targetAlgorithm(input);\n  const t1 = performance.now();\n  const duration = t1 - t0;\n  const ratio = prevTime && prevTime > 0.01 ? (duration / prevTime).toFixed(2) : 'N/A';\n  results.push({ N: n, 'Time (ms)': duration.toFixed(2), 'Ratio T(2N)/T(N)': ratio });\n  prevTime = duration;\n}\n\nconsole.table(results);"
  }
}
```

### Safety Policy in MCP
- **Strict Sandbox**: `nodejs-executor` enforces `--allow-fs-write=<tempDir>` and blocks child processes, ensuring untrusted micro-benchmarks cannot modify workspace files or leak credentials.
- **Adaptive Batching & Median Filtering**: For sub-millisecond functions, repetitions are dynamically accumulated until elapsed time exceeds timer resolution ($> 3\text{ms}$), and medians are used for runs between $1\text{ms}$ and $50\text{ms}$.
- **Runaway Timeout Protection**: The benchmark harness aborts any input scale exceeding $3,000\text{ms}$, while the host MCP server enforces a $30,000\text{ms}$ hard process kill to guard against exponential blowups.
- **Async Support**: Transparently supports `async` functions with top-level `await`.
- **Pre-packaged Harness Script**: Available at `.github/skills/algorithmic-complexity-analyzer/scripts/benchmark-harness.mjs` for programmatic import or direct CLI execution.

---

## 3. Auxiliary Space Empirical Verification

To verify auxiliary memory complexity ($O(1)$ vs $O(n)$ heap consumption), measure the delta in heap allocations using `process.memoryUsage().heapUsed`:

```typescript
function measureMemoryDelta(fn: () => void): number {
  if (global.gc) global.gc();
  const before = process.memoryUsage().heapUsed;
  fn();
  const after = process.memoryUsage().heapUsed;
  return Math.max(0, after - before);
}
```

### Interpretation of Memory Ratios:
- **$\Delta \text{Heap}(2N) / \Delta \text{Heap}(N) \approx 1.0$**: Confirms **$O(1)$ Auxiliary Space** (in-place manipulation, primitive pointers).
- **$\Delta \text{Heap}(2N) / \Delta \text{Heap}(N) \approx 2.0$**: Confirms **$O(n)$ Auxiliary Space** (hash map, cloned array, or recursion call frames).
- **$\Delta \text{Heap}(2N) / \Delta \text{Heap}(N) \approx 4.0$**: Confirms **$O(n^2)$ Auxiliary Space** (2D matrix allocation, Cartesian product table).

---

## 4. Cross-Language Empirical Translation

While `nodejs-executor` executes JavaScript and TypeScript, asymptotic complexity is **language-independent**.

When auditing Python, C#, Java, or Go code:
1. Isolate the core mathematical logic or inner loop kernel.
2. Formulate a 10-line JS/TS equivalent representing the same data structures (e.g. `Map` for Java `HashMap` / Python `dict`, `Array` for `List`).
3. Run the doubling hypothesis via `execute_code`.
4. Validate whether the theoretical Big-O matches the observed $T(2N)/T(N)$ growth ratio.

