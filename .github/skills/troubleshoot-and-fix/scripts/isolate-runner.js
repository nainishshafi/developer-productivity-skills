#!/usr/bin/env node
/**
 * isolate-runner.js — Scaffold an isolated reproduction testbed for troubleshooting.
 *
 * Usage:
 *   node isolate-runner.js init --name <issue_name> --lang <ts|js|python|java|csharp> [--dir <output_dir>]
 */

const fs = require('node:fs');
const path = require('node:path');

const TEMPLATES = {
  ts: (name, cleanName, date, filename) => `// Isolated Reproduction Testbed: ${name}
// Created: ${date}
// Run with: npx tsx ${filename} or npx ts-node ${filename}

import assert from 'node:assert/strict';

// ==============================================================================
// 1. EXTRACTED CODE (Extracted minimal logic under investigation)
// ==============================================================================
interface TargetInput {
  id: string;
  value?: number | null;
}

function targetFunction(payload: TargetInput): { id: string; result: number } {
  // TODO: Paste extracted logic here
  throw new Error('Reproduction logic not yet implemented');
}

// ==============================================================================
// 2. MOCK DATA & FIXTURES
// ==============================================================================
const mockInputPassing: TargetInput = {
  id: 'item_123',
  value: 100,
};

const mockInputFailing: TargetInput = {
  id: 'item_456',
  value: null, // Example triggering edge case
};

// ==============================================================================
// 3. REPRODUCTION HARNESS (Direct assertions)
// ==============================================================================
async function runHarness() {
  console.log('Testing happy path...');
  const res1 = targetFunction(mockInputPassing);
  assert.equal(res1.result, 100);
  console.log('✔ Happy path passed.');

  console.log('Testing failure case (reproduction)...');
  const res2 = targetFunction(mockInputFailing);
  assert.equal(res2.result, 0);
  console.log('✔ Failure case successfully handled and verified!');
}

runHarness().catch((err) => {
  console.error('\\n❌ REPRODUCTION / VERIFICATION ERROR:');
  console.error(err);
  process.exit(1);
});
`,

  js: (name, cleanName, date, filename) => `// Isolated Reproduction Testbed: ${name}
// Created: ${date}
// Run with: node ${filename}

const assert = require('node:assert/strict');

// ==============================================================================
// 1. EXTRACTED CODE (Extracted minimal logic under investigation)
// ==============================================================================
function targetFunction(payload) {
  // TODO: Paste extracted logic here
  throw new Error('Reproduction logic not yet implemented');
}

// ==============================================================================
// 2. MOCK DATA & FIXTURES
// ==============================================================================
const mockPassing = { id: 'item_123', value: 100 };
const mockFailing = { id: 'item_456', value: null };

// ==============================================================================
// 3. REPRODUCTION HARNESS
// ==============================================================================
function runHarness() {
  console.log('Testing happy path...');
  const res1 = targetFunction(mockPassing);
  assert.equal(res1.result, 100);

  console.log('Testing failure reproduction...');
  const res2 = targetFunction(mockFailing);
  assert.equal(res2.result, 0);

  console.log('✔ Verified!');
}

try {
  runHarness();
} catch (err) {
  console.error('\\n❌ REPRODUCTION ERROR:');
  console.error(err);
  process.exit(1);
}
`,

  python: (name, cleanName, date, filename) => `# Isolated Reproduction Testbed: ${name}
# Created: ${date}
# Run with: python ${filename}

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
MOCK_INPUT_PASSING = {
    "id": "item_123",
    "value": 100,
}

MOCK_INPUT_FAILING = {
    "id": "item_456",
    "value": None,
}


# ==============================================================================
# 3. REPRODUCTION HARNESS
# ==============================================================================
class TestReproduction(unittest.TestCase):
    def test_happy_path(self):
        result = target_function(MOCK_INPUT_PASSING)
        self.assertIsNotNone(result)

    def test_edge_case_failure(self):
        result = target_function(MOCK_INPUT_FAILING)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
`,

  java: (name, cleanName, date, filename) => `// Isolated Reproduction Testbed: ${name}
// Created: ${date}
// Run with: java ${filename}

public class Repro_${cleanName} {

    public static int calculate(Integer value) {
        // TODO: Paste extracted logic here
        throw new UnsupportedOperationException("Reproduction logic not yet implemented");
    }

    public static void main(String[] args) {
        System.out.println("Running isolated reproduction testbed...");

        try {
            int res1 = calculate(100);
            System.out.println("✔ Happy path: " + res1);
        } catch (Exception e) {
            System.err.println("❌ Happy path failed: " + e.getMessage());
        }

        try {
            int res2 = calculate(null);
            System.out.println("✔ Edge case handled: " + res2);
        } catch (Exception e) {
            System.err.println("❌ Reproduced failure on edge case: " + e);
            e.printStackTrace();
        }
    }
}
`,

  csharp: (name, cleanName, date, filename) => `// Isolated Reproduction Testbed: ${name}
// Created: ${date}
// Run with: dotnet script ${filename} (or include in an xUnit test project)

using System;

public static class Repro_${cleanName}
{
    public static int Calculate(int? value)
    {
        // TODO: Paste extracted logic here
        throw new NotImplementedException("Reproduction logic not yet implemented");
    }

    public static void Main()
    {
        Console.WriteLine("Running isolated C# reproduction testbed...");

        int res1 = Calculate(100);
        Console.WriteLine($"✔ Happy path: {res1}");

        int res2 = Calculate(null);
        Console.WriteLine($"✔ Edge case handled: {res2}");
    }
}
`
};

const EXTENSIONS = {
  ts: 'ts',
  js: 'js',
  python: 'py',
  java: 'java',
  csharp: 'cs',
  cs: 'cs'
};

function parseArgs() {
  const args = process.argv.slice(2);
  const parsed = { command: args[0], dir: 'scratch/repro' };

  for (let i = 1; i < args.length; i++) {
    if (args[i] === '--name' && args[i + 1]) {
      parsed.name = args[++i];
    } else if (args[i] === '--lang' && args[i + 1]) {
      parsed.lang = args[++i].toLowerCase();
    } else if (args[i] === '--dir' && args[i + 1]) {
      parsed.dir = args[++i];
    }
  }
  return parsed;
}

function sanitizeName(name) {
  return name.replace(/[^a-zA-Z0-9-_]/g, '_').replace(/^[-_]+|[-_]+$/g, '');
}

function main() {
  const { command, name, lang, dir } = parseArgs();

  if (command !== 'init' || !name || !lang) {
    console.log('Usage: node isolate-runner.js init --name <issue_name> --lang <ts|js|python|java|csharp> [--dir <output_dir>]');
    process.exit(1);
  }

  const normalizedLang = lang === 'cs' ? 'csharp' : lang;

  if (!TEMPLATES[normalizedLang]) {
    console.error(`Error: Unsupported language '${lang}'. Choose from: ${Object.keys(TEMPLATES).join(', ')}`);
    process.exit(1);
  }

  const cleanName = sanitizeName(name);
  const ext = EXTENSIONS[normalizedLang];
  const filename = (normalizedLang === 'java' || normalizedLang === 'csharp')
    ? `Repro_${cleanName.replace(/-/g, '_')}.${ext}`
    : `repro_${cleanName}.${ext}`;
  const targetDir = path.resolve(process.cwd(), dir);
  const targetFile = path.join(targetDir, filename);

  fs.mkdirSync(targetDir, { recursive: true });

  if (fs.existsSync(targetFile)) {
    console.warn(`Warning: File '${targetFile}' already exists. Not overwriting.`);
    return;
  }

  const date = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const content = TEMPLATES[normalizedLang](name, cleanName.replace(/-/g, '_'), date, filename);

  fs.writeFileSync(targetFile, content, 'utf8');
  console.log(`Created isolated reproduction harness: ${targetFile}`);
}

main();

