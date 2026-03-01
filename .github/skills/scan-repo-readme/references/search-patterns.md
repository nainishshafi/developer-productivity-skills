# Search Patterns Reference

Reference guide for the `scan-repo-readme` skill — README file patterns, synonym groups, relevance scoring, and output format.

---

## README Filename Patterns

### Common filenames (search in this order)

| Filename | Notes |
|----------|-------|
| `README.md` | Most common; Markdown |
| `readme.md` | Lowercase variant |
| `README.rst` | reStructuredText (Python projects) |
| `README.txt` | Plain text |
| `README` | No extension |
| `README.adoc` | AsciiDoc |
| `README.org` | Org-mode |
| `CONTRIBUTING.md` | Contribution guide — often contains setup info |
| `CHANGELOG.md` | Version history — relevant for "what changed" queries |
| `docs/README.md` | Docs subfolder variant |

### Glob patterns for Glob tool

```
**/README.md
**/readme.md
**/README.rst
**/README.txt
**/README
**/README.adoc
```

### Directories to skip

- `.git/`
- `node_modules/`
- `__pycache__/`
- `.venv/`
- `dist/`, `build/`, `.next/`, `.nuxt/`
- Any directory starting with `.`

---

## Keyword Synonym Groups

When performing keyword search, expand the user's query using these synonym groups. Search for ALL synonyms, not just the original term.

| Topic | Keywords to search |
|-------|-------------------|
| Installation | install, setup, getting started, requirements, prerequisites, dependencies, pip install, npm install, brew, apt |
| Usage | usage, example, quickstart, quick start, how to use, tutorial, demo, run, execute |
| Configuration | config, configuration, settings, environment, .env, options, parameters |
| Authentication | auth, authentication, token, API key, credentials, login, secret |
| Deployment | deploy, deployment, production, release, publish, build |
| Testing | test, testing, pytest, jest, spec, unit test, integration |
| Contributing | contributing, contribute, pull request, PR, issue, bug report |
| License | license, licence, MIT, Apache, GPL, copyright |
| API | API, endpoint, route, REST, GraphQL, SDK |
| Database | database, db, schema, migration, SQL, SQLite, PostgreSQL, MongoDB |

---

## Section Extraction Heuristics

### Heading-based splitting

Split README content into sections at Markdown headings:
- `# Heading` → H1 (usually project title, skip as section boundary)
- `## Heading` → H2 (primary sections — use as main split points)
- `### Heading` → H3 (subsections)

Each section = heading text + all content until the next same-or-higher-level heading.

### Content types to prioritize

| Content type | Relevance indicator |
|-------------|---------------------|
| Code blocks (```) | High — executable instructions |
| Numbered lists | High — step-by-step procedures |
| Bullet lists with commands | High — usage examples |
| Badge lines (shields.io) | Low — skip |
| Table of contents links | Low — skip |
| License boilerplate | Low unless query is about license |

---

## Semantic Relevance Scoring

Score each section as **HIGH**, **MEDIUM**, or **LOW**:

### HIGH
- Section directly answers the user's query
- Contains the procedure, value, or explanation the user asked for
- Examples: "Installation" section for "how do I install", "API" section for "what endpoints exist"

### MEDIUM
- Section is related context that helps understand the query topic
- Adjacent procedures or prerequisites
- Examples: "Requirements" for an install query, "Overview" for any query

### LOW
- Section is tangential — same repo, different topic
- Boilerplate, badges, table of contents, license text (unless queried)

---

## Output File Format

The haiku agent writes the report to the timestamped file in this format:

```markdown
# README Scan Report
Query: {user query or "full summary"}
Scanned: {timestamp}
Files: {number of README files found}

---

## {/path/to/README.md}

### HIGH Relevance — {Section Heading}

> {Quoted text from source}

---

### MEDIUM Relevance — {Section Heading}

> {Quoted text}

---

## {/path/to/other/README.md}

...
```

For full summary (no query), use:

```markdown
## {/path/to/README.md}

**Project**: {name}
**Description**: {one-liner}

**Features**:
- {feature 1}
- {feature 2}

**Installation**: {steps}

**Usage**: {example}

**License**: {license type}
```

---

## Python Interpreter Resolution

Always resolve in this order:
1. `.venv/Scripts/python` — Windows virtualenv
2. `.venv/bin/python` — Unix/macOS virtualenv
3. `python3` — system fallback
4. `python` — last resort

Check existence with `Path(".venv/Scripts/python").exists()` before using.
