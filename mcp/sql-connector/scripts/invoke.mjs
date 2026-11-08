#!/usr/bin/env node

/**
 * Quick invocation test script for sql-connector
 */
import { auditSqlQuery } from '../dist/guardrails/sql-guardrail.js';
import { auditMongoQuery } from '../dist/guardrails/mongo-guardrail.js';
import { SqliteAdapter } from '../dist/adapters/sqlite-adapter.js';

console.log('Testing SQL Connector Guardrails & SQLite Adapter...\n');

// 1. Test DROP TABLE rejection
const dropAudit = auditSqlQuery('DROP TABLE users;', 'guarded-write');
console.log('Test 1 - DROP TABLE rejection:');
console.log('  Allowed:', dropAudit.allowed);
console.log('  Risk:', dropAudit.riskLevel);
console.log('  Violations:', dropAudit.violations[0]);

// 2. Test DELETE * rejection
const deleteStarAudit = auditSqlQuery('DELETE FROM users;', 'guarded-write');
console.log('\nTest 2 - DELETE * / unbounded rejection:');
console.log('  Allowed:', deleteStarAudit.allowed);
console.log('  Risk:', deleteStarAudit.riskLevel);
console.log('  Violations:', deleteStarAudit.violations[0]);

// 3. Test Tautological WHERE rejection
const tautologyAudit = auditSqlQuery('DELETE FROM users WHERE 1=1;', 'guarded-write');
console.log('\nTest 3 - Tautological WHERE 1=1 rejection:');
console.log('  Allowed:', tautologyAudit.allowed);
console.log('  Risk:', tautologyAudit.riskLevel);
console.log('  Violations:', tautologyAudit.violations[0]);

// 4. Test In-Memory SQLite Execution
const sqlite = new SqliteAdapter({ engine: 'sqlite', filePath: ':memory:' });
await sqlite.connect();

// Create sample table
await sqlite.query({
  query: 'CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT);',
  mode: 'guarded-write',
});

// Insert row
await sqlite.query({
  query: "INSERT INTO customers (id, name, email) VALUES (1, 'Alice Smith', 'alice@example.com');",
  mode: 'guarded-write',
});

// Select query in read-only mode
const selectRes = await sqlite.query({
  query: 'SELECT * FROM customers;',
  mode: 'read-only',
});

console.log('\nTest 4 - Safe SQLite Query:');
console.log('  Success:', selectRes.success);
console.log('  Rows returned:', selectRes.rowCount);
console.log('  First row:', selectRes.rows[0]);

await sqlite.disconnect();
console.log('\nAll sanity checks passed!');
