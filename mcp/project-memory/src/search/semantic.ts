import { MemoryRecord, MemorySummary } from '../types.js';

export const VECTOR_DIMENSION = 256;
export const SEMANTIC_WEIGHT = 0.40;
export const LEXICAL_WEIGHT = 0.60;

/**
 * Generates a normalized 256-dimensional semantic subword embedding vector.
 * Uses character 3-grams, 4-grams, and word tokens hashed into dense float buckets.
 * Zero external network or model dependencies; runs with 100% determinism.
 */
export function generateEmbedding(text: string): number[] {
  const vec = new Float64Array(VECTOR_DIMENSION);
  const normalized = text.toLowerCase().replace(/[^a-z0-9_\-\s]/g, ' ');
  const words = normalized.split(/\s+/).filter(Boolean);

  // 1. Word-level hashing with frequency weighting
  for (const word of words) {
    const h = hashString(word);
    const idx = Math.abs(h) % VECTOR_DIMENSION;
    vec[idx] += 1.5;

    // 2. Character n-grams (3-grams and 4-grams) for subword & morphological similarity
    if (word.length >= 3) {
      for (let i = 0; i <= word.length - 3; i++) {
        const trigram = word.substring(i, i + 3);
        const triIdx = Math.abs(hashString(trigram)) % VECTOR_DIMENSION;
        vec[triIdx] += 0.8;
      }
    }
    if (word.length >= 4) {
      for (let i = 0; i <= word.length - 4; i++) {
        const fourgram = word.substring(i, i + 4);
        const fourIdx = Math.abs(hashString(fourgram)) % VECTOR_DIMENSION;
        vec[fourIdx] += 0.6;
      }
    }
  }

  // L2 Normalize the vector
  let norm = 0;
  for (let i = 0; i < VECTOR_DIMENSION; i++) {
    norm += vec[i] * vec[i];
  }
  norm = Math.sqrt(norm);

  const result: number[] = new Array(VECTOR_DIMENSION);
  if (norm > 0) {
    for (let i = 0; i < VECTOR_DIMENSION; i++) {
      result[i] = Number((vec[i] / norm).toFixed(6));
    }
  } else {
    for (let i = 0; i < VECTOR_DIMENSION; i++) {
      result[i] = 0;
    }
  }

  return result;
}

/**
 * Calculates Cosine Similarity between two normalized vectors.
 */
export function cosineSimilarity(v1: number[], v2: number[]): number {
  if (v1.length !== v2.length || v1.length === 0) return 0;
  let dot = 0;
  for (let i = 0; i < v1.length; i++) {
    dot += v1[i] * v2[i];
  }
  return Math.max(0, Math.min(1, dot));
}

/**
 * Evaluates lexical (keyword/tag) matching score [0, 1].
 */
export function lexicalScore(query: string, record: { title: string; summary: string; tags: string[]; learnings: string }): number {
  const queryTerms = query.toLowerCase().split(/\s+/).filter((t) => t.length > 1);
  if (queryTerms.length === 0) return 0;

  const titleTokens = new Set(record.title.toLowerCase().split(/\s+/));
  const tagTokens = new Set(record.tags.map((t) => t.toLowerCase()));
  const bodyTokens = new Set((record.summary + ' ' + record.learnings).toLowerCase().split(/\s+/));

  let matchedWeight = 0;
  let totalWeight = 0;

  for (const term of queryTerms) {
    totalWeight += 2.0; // max potential per term
    if (tagTokens.has(term)) {
      matchedWeight += 2.0;
    } else if (titleTokens.has(term)) {
      matchedWeight += 1.8;
    } else if (bodyTokens.has(term)) {
      matchedWeight += 1.0;
    } else {
      // Partial prefix/substring match
      const matchedTag = record.tags.some((t) => t.includes(term));
      const matchedTitle = record.title.toLowerCase().includes(term);
      if (matchedTag || matchedTitle) {
        matchedWeight += 0.8;
      }
    }
  }

  return Math.min(1, matchedWeight / Math.max(1, totalWeight));
}

/**
 * Hybrid Search Ranking (40% Semantic Cosine + 60% Lexical Match).
 * Returns strictly sanitized summaries without vector embeddings.
 */
export function rankMemories(
  query: string,
  memories: MemoryRecord[],
  limit = 5,
  minScore = 0.25
): MemorySummary[] {
  const queryVec = generateEmbedding(query);

  const scored = memories.map((record) => {
    const semantic = cosineSimilarity(queryVec, record.embedding);
    const lexical = lexicalScore(query, record);
    // Explicit 40% semantic, 60% lexical weighting
    const hybrid = Number((SEMANTIC_WEIGHT * semantic + LEXICAL_WEIGHT * lexical).toFixed(4));

    return {
      record,
      hybrid,
    };
  });

  return scored
    .filter((item) => item.hybrid >= minScore)
    .sort((a, b) => b.hybrid - a.hybrid)
    .slice(0, limit)
    .map(({ record, hybrid }) => ({
      id: record.id,
      category: record.category,
      title: record.title,
      summary: record.summary,
      learnings: record.learnings,
      tags: record.tags,
      createdAt: record.createdAt,
      updatedAt: record.updatedAt,
      relevanceScore: hybrid,
    }));
}

/**
 * 32-bit FNV-1a hash function for fast deterministic bucketing.
 */
function hashString(str: string): number {
  let hash = 2166136261;
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash;
}

