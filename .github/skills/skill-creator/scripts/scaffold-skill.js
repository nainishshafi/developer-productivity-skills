#!/usr/bin/env node
/**
 * scaffold-skill.js — Create boilerplate directory structure for a new Claude Code skill.
 * Works natively in Node.js environments (no Python dependency required).
 *
 * Usage:
 *   node scaffold-skill.js <skill-name> [base-path] [--modular]
 */

const fs = require('node:fs');
const path = require('node:path');

const SKILL_NAME_PATTERN = /^[a-z][a-z0-9-]+$/;

function skillTitle(skillName) {
  return skillName
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function validateSkillName(name) {
  if (!SKILL_NAME_PATTERN.test(name)) {
    console.error(
      `Error: '${name}' is not a valid skill name.\n` +
      `Skill names must start with a lowercase letter, contain only lowercase letters, digits, and hyphens.\n` +
      `Example: lint-python, deploy-staging, typescript-developer`
    );
    process.exit(1);
  }
  if (name.length > 64) {
    console.error(`Error: skill name '${name}' exceeds 64 characters.`);
    process.exit(1);
  }
}

function checkNotExists(dirPath, skillName) {
  if (fs.existsSync(dirPath)) {
    console.error(
      `Warning: skill directory already exists at '${dirPath}'.\n` +
      `Refusing to overwrite existing skill '${skillName}'.`
    );
    process.exit(1);
  }
}

function writeFile(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, 'utf8');
}

function main() {
  const rawArgs = process.argv.slice(2);
  const isModular = rawArgs.includes('--modular') || rawArgs.includes('-m');
  const args = rawArgs.filter((a) => a !== '--modular' && a !== '-m');

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(
      `Usage: node scaffold-skill.js <skill-name> [base-path] [--modular]\n\n` +
      `Arguments:\n` +
      `  skill-name   Lowercase kebab-case name (e.g., rust-developer)\n` +
      `  base-path    Root skills directory (default: .github/skills)\n` +
      `  --modular    Scaffold as a modular Knowledge-Pack (like java-developer)`
    );
    process.exit(args.length === 0 ? 1 : 0);
  }

  const skillName = args[0];
  const basePath = args[1] || '.github/skills';

  validateSkillName(skillName);
  const skillDir = path.join(basePath, skillName);
  checkNotExists(skillDir, skillName);

  const title = skillTitle(skillName);

  if (isModular) {
    const modularSkillMd = `---
name: ${skillName}
description: Expert architectural and engineering guidance for ${title}. Helps the LLM analyze architecture, apply clean design, enforce memory/performance hygiene, and adopt testing patterns pragmatically. Use when writing, reviewing, designing, or refactoring ${title} code.
version: 1.0.0
---

# ${title} Skill

You are an expert software engineer specializing in modern ${title}, clean architecture, memory safety, and performance.

## Core Directives

1. **Respect Project Baseline**: Check toolchain, runtime version, and existing libraries before introducing dependencies.
2. **Simplicity First (KISS & YAGNI)**: Favor straightforward, readable code over speculative abstractions.
3. **Memory & Performance Hygiene**: Proactively avoid closure scope leaks, unbounded collections, event loop blocking, and resource leaks.
4. **Follow Established Conventions**: Match codebase patterns over personal stylistic preferences.

## Knowledge Modules

Load only the modules relevant to the task.

- [Architecture & Domain Modeling](core/architecture.md)
- [Memory Safety & Closures](runtime-and-memory/memory-and-closures.md)
- [Performance & Concurrency](concurrency/concurrency.md)
- [Security Guidelines](security/security.md)
- [Testing & Quality Best Practices](testing/best-practices.md)
`;

    const files = [
      [path.join(skillDir, 'SKILL.md'), modularSkillMd],
      [path.join(skillDir, 'core', 'architecture.md'), `# ${title} Architecture & Domain Modeling\n\nTODO\n`],
      [path.join(skillDir, 'runtime-and-memory', 'memory-and-closures.md'), `# ${title} Memory Safety & Closures\n\nTODO\n`],
      [path.join(skillDir, 'concurrency', 'concurrency.md'), `# ${title} Concurrency & Performance\n\nTODO\n`],
      [path.join(skillDir, 'security', 'security.md'), `# ${title} Security Guidelines\n\nTODO\n`],
      [path.join(skillDir, 'testing', 'best-practices.md'), `# ${title} Testing Best Practices\n\nTODO\n`],
    ];

    for (const [filePath, content] of files) {
      writeFile(filePath, content);
      console.log(filePath);
    }
  } else {
    const taskSkillMd = `---
name: ${skillName}
description: TODO — describe when and why to use this skill, with trigger phrases.
version: 1.0.0
---

# ${title}

TODO — one-line summary.

## When to Use This Skill

- TODO

## Core Concepts

### Concept 1

TODO

## Implementation Patterns

### Pattern 1

TODO

## Best Practices

- TODO

## Common Pitfalls

### Pitfall 1
**Problem:** TODO
**Solution:** TODO

## Resources

- TODO
`;

    const refMd = `# ${title} Reference\n\nTODO — supporting reference material for ${skillName}.\n`;

    const skillMdPath = path.join(skillDir, 'SKILL.md');
    const refMdPath = path.join(skillDir, 'references', `${skillName}-reference.md`);
    const gitkeepPath = path.join(skillDir, 'scripts', '.gitkeep');

    writeFile(skillMdPath, taskSkillMd);
    writeFile(refMdPath, refMd);
    writeFile(gitkeepPath, '');

    console.log(skillMdPath);
    console.log(refMdPath);
    console.log(gitkeepPath);
  }
}

main();
