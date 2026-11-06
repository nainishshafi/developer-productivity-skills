#!/usr/bin/env python3
"""
isolate-runner.py — Scaffold an isolated reproduction testbed for troubleshooting.

Usage:
    python isolate-runner.py init --name <issue_name> --lang <python|ts|js|java> [--dir <output_dir>]
    python isolate-runner.py list

Examples:
    python isolate-runner.py init --name auth-token-expiry --lang python
    python isolate-runner.py init --name cart-total-calc --lang ts
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

TEMPLATES = {
    "python": '''# Isolated Reproduction Testbed: {name}
# Created: {date}
# Run with: python {filename}

import sys
import unittest

# ==============================================================================
# 1. EXTRACTED CODE (Extracted minimal logic under investigation)
# ==============================================================================
def target_function(payload: dict) -> dict:
    """
    Extracted logic to troubleshoot and fix.
    """
    # TODO: Paste extracted logic here
    raise NotImplementedError("Reproduction logic not yet implemented")


# ==============================================================================
# 2. MOCK DATA & FIXTURES
# ==============================================================================
MOCK_INPUT_PASSING = {{
    "id": "item_123",
    "value": 100,
}}

MOCK_INPUT_FAILING = {{
    "id": "item_456",
    "value": None,  # Example triggering edge case
}}


# ==============================================================================
# 3. REPRODUCTION HARNESS (Assertions proving failure then fix)
# ==============================================================================
class TestReproduction(unittest.TestCase):
    def test_happy_path(self):
        result = target_function(MOCK_INPUT_PASSING)
        self.assertIsNotNone(result)

    def test_edge_case_failure(self):
        """This test should reproduce the bug initially, then pass once fixed."""
        result = target_function(MOCK_INPUT_FAILING)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
''',
    "ts": '''// Isolated Reproduction Testbed: {name}
// Created: {date}
// Run with: npx tsx {filename} or npx ts-node {filename}

import assert from 'node:assert/strict';

// ==============================================================================
// 1. EXTRACTED CODE (Extracted minimal logic under investigation)
// ==============================================================================
interface TargetInput {{
  id: string;
  value?: number | null;
}}

function targetFunction(payload: TargetInput): {{ id: string; result: number }} {{
  // TODO: Paste extracted logic here
  throw new Error('Reproduction logic not yet implemented');
}}

// ==============================================================================
// 2. MOCK DATA & FIXTURES
// ==============================================================================
const mockInputPassing: TargetInput = {{
  id: 'item_123',
  value: 100,
}};

const mockInputFailing: TargetInput = {{
  id: 'item_456',
  value: null, // Example triggering edge case
}};

// ==============================================================================
// 3. REPRODUCTION HARNESS (Direct assertions)
// ==============================================================================
async function runHarness() {{
  console.log('Testing happy path...');
  const res1 = targetFunction(mockInputPassing);
  assert.equal(res1.result, 100);
  console.log('✔ Happy path passed.');

  console.log('Testing failure case (reproduction)...');
  const res2 = targetFunction(mockInputFailing);
  assert.equal(res2.result, 0);
  console.log('✔ Failure case successfully handled and verified!');
}}

runHarness().catch((err) => {{
  console.error('\\n❌ REPRODUCTION / VERIFICATION ERROR:');
  console.error(err);
  process.exit(1);
}});
''',
    "js": '''// Isolated Reproduction Testbed: {name}
// Created: {date}
// Run with: node {filename}

const assert = require('node:assert/strict');

// ==============================================================================
// 1. EXTRACTED CODE (Extracted minimal logic under investigation)
// ==============================================================================
function targetFunction(payload) {{
  // TODO: Paste extracted logic here
  throw new Error('Reproduction logic not yet implemented');
}}

// ==============================================================================
// 2. MOCK DATA & FIXTURES
// ==============================================================================
const mockPassing = {{ id: 'item_123', value: 100 }};
const mockFailing = {{ id: 'item_456', value: null }};

// ==============================================================================
// 3. REPRODUCTION HARNESS
// ==============================================================================
function runHarness() {{
  console.log('Testing happy path...');
  const res1 = targetFunction(mockPassing);
  assert.equal(res1.result, 100);

  console.log('Testing failure reproduction...');
  const res2 = targetFunction(mockFailing);
  assert.equal(res2.result, 0);

  console.log('✔ Verified!');
}}

try {{
  runHarness();
}} catch (err) {{
  console.error('\\n❌ REPRODUCTION ERROR:');
  console.error(err);
  process.exit(1);
}}
''',
    "java": '''// Isolated Reproduction Testbed: {name}
// Created: {date}
// Run with: java {filename} (Java 11+ single file execution)

public class Repro_{clean_name} {{

    // 1. EXTRACTED LOGIC
    public static int calculate(Integer value) {{
        // TODO: Paste extracted logic here
        throw new UnsupportedOperationException("Reproduction logic not yet implemented");
    }}

    // 2. HARNESS & MOCK DATA
    public static void main(String[] args) {{
        System.out.println("Running isolated reproduction testbed...");

        // Happy path
        try {{
            int res1 = calculate(100);
            System.out.println("✔ Happy path: " + res1);
        }} catch (Exception e) {{
            System.err.println("❌ Happy path failed: " + e.getMessage());
        }}

        // Failing edge case
        try {{
            int res2 = calculate(null);
            System.out.println("✔ Edge case handled: " + res2);
        }} catch (Exception e) {{
            System.err.println("❌ Reproduced failure on edge case: " + e);
            e.printStackTrace();
        }}
    }}
}}
'''
}

EXTENSIONS = {
    "python": "py",
    "ts": "ts",
    "js": "js",
    "java": "java",
}


def sanitize_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name).strip("-_")


def init_harness(name: str, lang: str, out_dir: str) -> str:
    lang = lang.lower()
    if lang not in TEMPLATES:
        print(f"Error: Unsupported language '{lang}'. Choose from: {', '.join(TEMPLATES.keys())}", file=sys.stderr)
        sys.exit(1)

    clean_name = sanitize_name(name)
    ext = EXTENSIONS[lang]
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    if lang == "java":
        filename = f"Repro_{clean_name}.java"
    else:
        filename = f"repro_{clean_name}.{ext}"

    file_path = target_dir / filename
    if file_path.exists():
        print(f"Warning: File '{file_path}' already exists. Not overwriting.", file=sys.stderr)
        return str(file_path)

    template = TEMPLATES[lang].format(
        name=name,
        clean_name=clean_name.replace("-", "_"),
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        filename=filename,
    )

    file_path.write_text(template, encoding="utf-8")
    print(f"Created isolated reproduction harness: {file_path}")
    return str(file_path)


def main():
    parser = argparse.ArgumentParser(description="Scaffold an isolated reproduction testbed for troubleshooting.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new isolated reproduction harness")
    init_parser.add_argument("--name", required=True, help="Short name/slug for the issue (e.g. auth-null-pointer)")
    init_parser.add_argument("--lang", required=True, choices=["python", "ts", "js", "java"], help="Target language")
    init_parser.add_argument("--dir", default="scratch/repro", help="Directory where harness will be saved (default: scratch/repro)")

    args = parser.parse_args()
    if args.command == "init":
        init_harness(args.name, args.lang, args.dir)


if __name__ == "__main__":
    main()

