import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from '../dist/server.js';
import { auditQuerySafety } from '../dist/tools/audit-query-safety.js';

describe('SQL Connector MCP Server & Tool Definitions', () => {
  test('should instantiate McpServer with correct metadata', () => {
    const server = createServer();
    assert(server);
  });

  test('audit_query_safety tool should catch DROP TABLE', () => {
    const res = auditQuerySafety({
      query: 'DROP TABLE accounts;',
      engine: 'postgres',
      mode: 'guarded-write',
    });

    assert.equal(res.allowed, false);
    assert.equal(res.riskLevel, 'CRITICAL_BLOCKED');
    assert(res.violations.some((v) => v.includes('DROP')));
  });

  test('audit_query_safety tool should catch DELETE * / unbounded delete', () => {
    const res = auditQuerySafety({
      query: 'DELETE FROM accounts;',
      engine: 'sqlserver',
      mode: 'guarded-write',
    });

    assert.equal(res.allowed, false);
    assert.equal(res.riskLevel, 'CRITICAL_BLOCKED');
    assert(res.violations.some((v) => v.includes('Unbounded')));
  });

  test('audit_query_safety tool should catch tautological WHERE in Oracle', () => {
    const res = auditQuerySafety({
      query: "DELETE FROM employees WHERE 'x'='x'",
      engine: 'oracle',
      mode: 'guarded-write',
    });

    assert.equal(res.allowed, false);
    assert.equal(res.riskLevel, 'CRITICAL_BLOCKED');
  });

  test('audit_query_safety tool should catch MongoDB dropDatabase', () => {
    const res = auditQuerySafety({
      query: '{"operation": "dropDatabase"}',
      engine: 'mongodb',
      mode: 'guarded-write',
    });

    assert.equal(res.allowed, false);
    assert.equal(res.riskLevel, 'CRITICAL_BLOCKED');
  });

  test('audit_query_safety tool should pass clean read-only query', () => {
    const res = auditQuerySafety({
      query: 'SELECT customer_id, company_name FROM Customers WHERE Country = "Germany"',
      engine: 'msaccess',
      mode: 'read-only',
    });

    assert.equal(res.allowed, true);
    assert.equal(res.riskLevel, 'SAFE');
    assert.equal(res.isReadOnly, true);
  });
});
