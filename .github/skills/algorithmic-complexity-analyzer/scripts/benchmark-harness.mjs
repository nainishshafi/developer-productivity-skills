#!/usr/bin/env node
/**
 * Asymptotic Doubling Hypothesis Benchmark Harness
 * 
 * Empirically determines Big-O time and space complexity classes
 * by measuring execution duration across exponential input sizes (N -> 2N).
 *
 * Usage:
 *   node .github/skills/algorithmic-complexity-analyzer/scripts/benchmark-harness.mjs
 */

import { performance } from 'node:perf_hooks';
import { pathToFileURL } from 'node:url';

/**
 * Runs the doubling test on a target function.
 * @param {string} name - Algorithm label
 * @param {(n: number) => unknown} setup - Generates input payload for size N
 * @param {(input: unknown) => unknown | Promise<unknown>} fn - Target algorithm to test
 * @param {number[]} sizes - Input sizes to test (must be doubling sequences, e.g. 500, 1000, 2000, 4000)
 * @returns {Promise<{ name: string, rows: Array<object>, detectedBound: string, avgRatio: number }>}
 */
export async function benchmarkAsymptotics(name, setup, fn, sizes = [500, 1000, 2000, 4000, 8000]) {
  console.log(`\n===============================================================`);
  console.log(`Empirical Asymptotic Benchmark: ${name}`);
  console.log(`===============================================================`);

  // JIT Warmup
  try {
    const warmupData = setup(100);
    for (let i = 0; i < 5; i++) {
      await fn(warmupData);
    }
  } catch {
    // Warmup best-effort
  }

  const rows = [];
  let prevDuration = null;

  for (const n of sizes) {
    try {
      const data = setup(n);
      if (typeof global.gc === 'function') {
        global.gc();
      }
      const startHeap = process.memoryUsage().heapUsed;

      // Adaptive batching: if function is ultra-fast (< 1ms), accumulate repetitions
      // to exceed timer jitter floor (> 3ms total elapsed)
      const tInit = performance.now();
      await fn(data);
      const firstEst = performance.now() - tInit;

      let medianDuration = firstEst;
      if (firstEst < 1.0) {
        const batchCount = Math.max(5, Math.min(200, Math.ceil(3 / Math.max(0.02, firstEst))));
        const batchStart = performance.now();
        for (let b = 0; b < batchCount; b++) {
          await fn(data);
        }
        medianDuration = (performance.now() - batchStart) / batchCount;
      } else if (firstEst <= 50) {
        // Multi-sample median for durations between 1ms and 50ms
        const samples = [firstEst];
        for (let i = 1; i < 3; i++) {
          const s = performance.now();
          await fn(data);
          samples.push(performance.now() - s);
        }
        samples.sort((a, b) => a - b);
        medianDuration = samples[Math.floor(samples.length / 2)];
      }
      const endHeap = process.memoryUsage().heapUsed;
      const heapDeltaKb = Math.max(0, (endHeap - startHeap) / 1024);

      let ratio = 'N/A';
      if (prevDuration !== null && prevDuration > 0.005) {
        ratio = (medianDuration / prevDuration).toFixed(2);
      }

      rows.push({
        N: n,
        'Time (ms)': Number(medianDuration.toFixed(3)),
        'Ratio T(2N)/T(N)': ratio,
        'Heap Delta (KB)': Number(heapDeltaKb.toFixed(1)),
      });

      prevDuration = medianDuration;

      // Abort if duration exceeds 3000ms to prevent process freeze on exponential algorithms
      if (medianDuration > 3000) {
        console.warn(`[ABORT] N=${n} took ${(medianDuration / 1000).toFixed(1)}s. Halting larger sizes to prevent lockup.`);
        break;
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      rows.push({
        N: n,
        'Time (ms)': 'ERROR',
        'Ratio T(2N)/T(N)': 'FAIL',
        'Heap Delta (KB)': 0,
      });
      console.error(`Error executing N=${n}: ${errorMsg}`);
      break;
    }
  }

  console.table(rows);

  // Classify detected class from last 2 ratios
  const validRatios = rows
    .map(r => parseFloat(r['Ratio T(2N)/T(N)']))
    .filter(r => !isNaN(r));

  let detectedBound = 'Undetermined';
  let avgRatio = 1.0;

  if (validRatios.length > 0) {
    avgRatio = validRatios.slice(-2).reduce((a, b) => a + b, 0) / Math.min(2, validRatios.length);
    if (avgRatio < 1.4) detectedBound = 'O(1) / O(log n)';
    else if (avgRatio < 2.4) detectedBound = 'O(n) Linear';
    else if (avgRatio < 3.2) detectedBound = 'O(n log n) Linearithmic';
    else if (avgRatio < 5.5) detectedBound = 'O(n^2) Quadratic [WARNING]';
    else detectedBound = 'O(n^3+) Polynomial / Exponential [CRITICAL]';

    console.log(`Empirical Asymptotic Classification: ${detectedBound} (Average Doubling Ratio: ${avgRatio.toFixed(2)}x)`);
  }

  return { name, rows, detectedBound, avgRatio };
}

// Self-test demonstration if executed directly
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  console.log('Running built-in benchmark demonstration...');

  (async () => {
    // Test 1: Linear Scan with Set lookup -> O(n)
    await benchmarkAsymptotics(
      'Linear Lookup with Set - O(n)',
      (n) => {
        const arr = Array.from({ length: n }, (_, i) => i);
        const set = new Set(arr);
        return { arr, set };
      },
      ({ arr, set }) => {
        let found = 0;
        for (let i = 0; i < arr.length; i++) {
          if (set.has(i)) found++;
        }
        return found;
      },
      [10000, 20000, 40000, 80000]
    );

    // Test 2: Quadratic Nested Scan with Array.includes -> O(n^2)
    await benchmarkAsymptotics(
      'Hidden Quadratic Scan (arr.includes in loop) - O(n^2)',
      (n) => Array.from({ length: n }, (_, i) => i),
      (arr) => {
        let found = 0;
        for (let i = 0; i < arr.length; i++) {
          if (arr.includes(-1)) found++;
        }
        return found;
      },
      [1000, 2000, 4000, 8000]
    );

    // Test 3: Asynchronous Function Demonstration
    await benchmarkAsymptotics(
      'Async Set Construction - O(n)',
      (n) => Array.from({ length: n }, (_, i) => `item_${i}`),
      async (arr) => {
        await Promise.resolve();
        const set = new Set();
        for (let i = 0; i < arr.length; i++) {
          set.add(arr[i]);
        }
        return set.size;
      },
      [5000, 10000, 20000, 40000]
    );
  })().catch(err => {
    console.error('Benchmark execution error:', err);
    process.exit(1);
  });
}
