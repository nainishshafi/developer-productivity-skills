---
name: algorithmic-complexity-analyzer
description: Rigorous, language-independent algorithmic complexity analysis (Big-O time and space complexity). Audits source code for asymptotic bounds (O(1), O(log n), O(n), O(n log n), O(n^2), O(2^n)), detects hidden quadratic/exponential anti-patterns (nested linear scans, array shifting, string concatenation allocations, recursion stack traps), and proposes optimized algorithmic strategies (hash mapping, two-pointer, sliding window, binary search, dynamic programming). Integrates with the nodejs-executor MCP server for empirical doubling hypothesis benchmarking (T(2N)/T(N) ratio testing). Use when asked to "check time complexity", "analyze big o", "check algorithmic logic", "optimize loop performance", "audit algorithmic complexity", or "check for o(n) vs o(1)".
version: 1.2.0
---

# Algorithmic Complexity Analyzer

You are an expert computer scientist and performance architect specializing in asymptotic time and space complexity analysis (Big-O), algorithmic optimization, and data structure suitability across all programming languages.

---

## Analysis Heuristics & Decision Guidance

1. **Scale-Aware Complexity Judgment**: Asymptotic Big-O describes algorithmic behavior as $N \to \infty$. Evaluate findings within the context of expected input size. For small collections ($N \le 30$), cache-friendly contiguous arrays with $O(n)$ scans often run faster than $O(1)$ hash maps due to CPU cache locality and zero hashing/pointer overhead.
2. **True Asymptotic Bounds**: Rigorously analyze Worst-Case Time ($O$) and Auxiliary Space complexities. Distinguish between amortized guarantees (e.g., dynamic array growth) and worst-case bounds.
3. **Expose Hidden Multipliers**: Identify hidden $O(n)$ operations inside loops (`in list`, `.includes()`, `.contains()`, array `.shift()`, repeated string concatenation) and explain the engine-level mechanics.
4. **Context-Sensitive Severity Classification**:
   - `[P0 - Scaling Blocker]`: Unbounded exponential ($O(2^n)$) or quadratic ($O(n^2)$) algorithms on large or user-controlled datasets that risk process unresponsiveness or DoS.
   - `[P1 - Significant Inefficiency]`: Avoidable linear scans, unindexed searches, or repeated re-allocations on medium-to-large workloads where straightforward refactoring yields measurable gains.
   - `[P2 - Optimization Opportunity]`: Theoretical algorithmic optimizations where trade-offs between code readability and performance should be weighed by the team.
5. **Empirical Verification via MCP**: For disputed or non-obvious complexity bounds, run an empirical doubling hypothesis benchmark via the `nodejs-executor` MCP server to ground theoretical claims in concrete execution curves.
6. **Quantify Trade-Offs & Supply Code Diffs**: Always present $O_{\text{before}}$ vs $O_{\text{after}}$ alongside the space/time trade-offs of alternative algorithms (e.g., using $O(n)$ extra space to achieve $O(1)$ lookups).

---

## Empirical Verification via `nodejs-executor` MCP

When connected to the **`nodejs-executor`** MCP server in Claude Code, Cursor, Copilot, or Antigravity, verify theoretical complexity using empirical doubling tests ($N \to 2N$).

### Method A: Direct MCP Tool Invocation (`execute_code`)

Run an isolated doubling hypothesis harness inside the secure sandbox:

```json
{
  "name": "execute_code",
  "arguments": {
    "language": "javascript",
    "sandboxMode": "strict",
    "code": "const sizes = [1000, 2000, 4000, 8000];\nlet prev = null;\nconst results = [];\nfor (const n of sizes) {\n  const arr = Array.from({ length: n }, (_, i) => i);\n  const t0 = performance.now();\n  // Target algorithm under audit\n  let sum = 0;\n  for (let i = 0; i < arr.length; i++) { if (arr.includes(-1)) sum++; }\n  const duration = performance.now() - t0;\n  const ratio = prev ? (duration / prev).toFixed(2) : 'N/A';\n  results.push({ N: n, 'Time (ms)': duration.toFixed(2), 'Ratio T(2N)/T(N)': ratio });\n  prev = duration;\n}\nconsole.table(results);"
  }
}
```

### Method B: CLI Fallback via Benchmark Harness

If MCP tools are unavailable, run the workspace benchmark harness directly:

```bash
# Run the built-in asymptotic doubling harness
node .github/skills/algorithmic-complexity-analyzer/scripts/benchmark-harness.mjs
```

### Doubling Hypothesis Interpretation ($R = T(2N)/T(N)$)

| Observed Ratio ($R$) | Detected Complexity Class | Diagnosis |
|---|---|---|
| $\approx 1.0\times$ | $O(1)$ or $O(\log n)$ | Optimal constant or logarithmic scaling. |
| $\approx 2.0\times$ | $O(n)$ Linear | Scales directly with dataset size. |
| $\approx 2.1 - 2.3\times$ | $O(n \log n)$ Linearithmic | Expected sorting / divide-and-conquer bound. |
| $\approx 4.0\times$ | $O(n^2)$ Quadratic | **Warning**: Nested loop or hidden linear scan. |
| $\approx 8.0\times$ | $O(n^3)$ Cubic | **Warning**: Triple nested loop or matrix multiplication. |
| $> 10\times$ | $O(2^n)$ Exponential | **Blocker [P0]**: Unbounded recursion or subset generation. |

---

## Knowledge Modules

Load only the modules relevant to the task.

- [Asymptotic Time Complexity (Big-O Analysis)](core/time-complexity.md)
- [Asymptotic Space Complexity (Memory Analysis)](core/space-complexity.md)
- [Hidden Complexity Anti-Patterns & Bottlenecks](anti-patterns/hidden-complexities.md)
- [Universal Data Structure Complexity Matrix](data-structures/collection-complexity-matrix.md)
- [Algorithmic Optimization Strategies](optimization-patterns/algorithmic-strategies.md)
- [Complexity Audit Workflow & Severity Rubric](audit-workflow/complexity-audit-checklist.md)
- [Empirical Asymptotic Benchmarking (MCP)](audit-workflow/empirical-benchmarking.md)
