import { MemoryCategory } from '../types.js';

export interface SanitizedInput {
  category: MemoryCategory;
  title: string;
  summary: string;
  learnings: string;
  tags: string[];
}

const FORBIDDEN_PLACEHOLDERS = new Set(['none', 'n/a', 'nothing', 'no', 'nil', 'null', 'na', 'tbd']);
const CONTROL_AND_BIDI_RE = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\u202A-\u202E\u2066-\u2069]/g;
const SECRET_PATTERNS: Array<[RegExp, string]> = [
  [/-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g, '[REDACTED_PRIVATE_KEY]'],
  [/\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g, '[REDACTED_AWS_KEY]'],
  [/\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b/g, '[REDACTED_GITHUB_TOKEN]'],
  [/\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b/g, '[REDACTED_API_KEY]'],
  [/\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g, '[REDACTED_JWT]'],
  [/(https?:\/\/)[^:\s/@"'<>]+:[^:\s/@"'<>]{3,}@/gi, '$1[REDACTED_CREDS]@'],
];

function cleanTextField(text: string): string {
  let cleaned = text.replace(CONTROL_AND_BIDI_RE, '');
  for (const [pattern, replacement] of SECRET_PATTERNS) {
    cleaned = cleaned.replace(pattern, replacement);
  }
  return cleaned.trim();
}

/**
 * Validates and sanitizes memory inputs across the 3 categories:
 * - ledger: Important to the project (permanent architecture, rules, decisions)
 * - sidecar: What is currently working on (transient task state, WIP context)
 * - journal: Summary of the current session with learnings
 */
export function sanitizeMemoryInput(raw: {
  category: string;
  title: string;
  summary: string;
  learnings: string;
  tags?: string[];
}): SanitizedInput {
  // 1. Validate Category
  const cat = raw.category?.trim().toLowerCase();
  if (cat !== 'ledger' && cat !== 'sidecar' && cat !== 'journal') {
    throw new Error(
      `Invalid category "${raw.category}". Must be exactly one of: "ledger" (important to project), "sidecar" (what is currently working on), or "journal" (summary of the current session with learnings).`
    );
  }

  // 2. Validate & Clean Title
  let title = cleanTextField(raw.title || '');
  if (!title) {
    throw new Error('Memory title cannot be empty.');
  }
  if (title.length > 150) {
    title = title.substring(0, 147) + '...';
  }

  // 3. Validate & Clean Summary (Strict anti-bloat guard)
  let summary = cleanTextField(raw.summary || '');
  if (!summary) {
    throw new Error(
      cat === 'journal'
        ? 'Journal memories require a summary of the current session alongside the learnings.'
        : 'Memory summary cannot be empty. Always provide a concise, high-signal summary.'
    );
  }

  // Detect and strip stack traces
  if (/(\bat\s+[\w\.\/<>]+\s+\(.*:\d+:\d+\)|\bnode:internal\/)/.test(summary)) {
    summary = summary
      .split('\n')
      .filter((line) => !/^\s*at\s+/.test(line) && !/^\s*node:internal/.test(line))
      .join('\n')
      .trim();
  }

  // Detect and strip base64 blobs
  summary = summary.replace(/[A-Za-z0-9+/_=-]{120,}/g, '[base64_data_removed]');
  if (!summary) {
    throw new Error('Memory summary cannot be empty after stripping stack traces or binary blobs.');
  }

  // Enforce max summary length: 1,500 characters
  if (summary.length > 1500) {
    throw new Error(
      `Summary is too bloated (${summary.length} characters; max 1500 allowed). Compress into key decisions and architectural bullet points only.`
    );
  }

  // 4. Validate Learnings (Mandatory: Mistakes and lessons learned)
  let learnings = cleanTextField(raw.learnings || '');
  if (!learnings || FORBIDDEN_PLACEHOLDERS.has(learnings.toLowerCase())) {
    throw new Error(
      'Learnings field cannot be empty. Always specify what mistakes or traps were encountered, the root cause, and the fix.'
    );
  }

  if (learnings.length < 10) {
    throw new Error(
      'Learnings description is too short. Please clearly detail the mistake or trap encountered and the concrete takeaway.'
    );
  }

  // Ensure journal entries do not just duplicate learnings as summary
  if (cat === 'journal' && summary.toLowerCase() === learnings.toLowerCase()) {
    throw new Error(
      'Journal entry needs a distinct session summary (what was worked on/accomplished) together with the learnings (mistakes made/avoided and takeaways). Do not supply identical text for both.'
    );
  }

  if (learnings.length > 1000) {
    learnings = learnings.substring(0, 997) + '...';
  }

  // 5. Sanitize Tags
  const rawTags = Array.isArray(raw.tags) ? raw.tags : [];
  const tags = Array.from(
    new Set(
      rawTags
        .map((t) => String(t).trim().toLowerCase().replace(/[^a-z0-9-_]/g, ''))
        .filter((t) => t.length > 1 && t.length <= 30)
    )
  ).slice(0, 8); // Max 8 tags

  return {
    category: cat as MemoryCategory,
    title,
    summary,
    learnings,
    tags,
  };
}
