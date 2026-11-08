import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { auditSqlQuery } from '../dist/guardrails/sql-guardrail.js';
import { auditMongoQuery } from '../dist/guardrails/mongo-guardrail.js';

describe('SQL Connector Guardrail Engine', () => {
  describe('Zero-Tolerance Destructive DDL Defense', () => {
    test('should strictly block DROP TABLE in any case', () => {
      const queries = [
        'DROP TABLE users;',
        'drop table customers;',
        'DROP TABLE IF EXISTS accounts;',
        '/* comment */ DROP TABLE orders;',
        'DROP/**/TABLE payments;',
      ];

      for (const q of queries) {
        const audit = auditSqlQuery(q, 'guarded-write');
        assert.equal(audit.allowed, false, `Expected query to be blocked: ${q}`);
        assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
        assert(audit.violations.some((v) => v.includes('DROP')));
      }
    });

    test('should strictly block DROP DATABASE, SCHEMA, VIEW, INDEX', () => {
      const queries = [
        'DROP DATABASE production;',
        'DROP SCHEMA public CASCADE;',
        'DROP VIEW active_users;',
        'DROP INDEX idx_user_email;',
        'DROP PROCEDURE sp_wipe_data;',
      ];

      for (const q of queries) {
        const audit = auditSqlQuery(q, 'guarded-write');
        assert.equal(audit.allowed, false);
        assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
      }
    });

    test('should strictly block TRUNCATE TABLE', () => {
      const queries = [
        'TRUNCATE TABLE audit_logs;',
        'truncate logs;',
        'TRUNCATE TABLE users;',
      ];

      for (const q of queries) {
        const audit = auditSqlQuery(q, 'guarded-write');
        assert.equal(audit.allowed, false);
        assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
      }
    });

    test('should strictly block ALTER TABLE ... DROP COLUMN', () => {
      const q = 'ALTER TABLE users DROP COLUMN password_hash;';
      const audit = auditSqlQuery(q, 'guarded-write');
      assert.equal(audit.allowed, false);
      assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
    });

    test('should strictly block dangerous system procedures', () => {
      const q = "EXEC xp_cmdshell 'powershell.exe whoami';";
      const audit = auditSqlQuery(q, 'guarded-write');
      assert.equal(audit.allowed, false);
      assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
    });
  });

  describe('Unbounded Destructive DML Defense', () => {
    test('should strictly block DELETE without WHERE clause (or DELETE *)', () => {
      const queries = [
        'DELETE FROM users;',
        'delete from customers',
        'DELETE * FROM accounts;',
        'DELETE users;',
      ];

      for (const q of queries) {
        const audit = auditSqlQuery(q, 'guarded-write');
        assert.equal(audit.allowed, false, `Expected unbounded DELETE to be blocked: ${q}`);
        assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
      }
    });

    test('should strictly block DELETE with tautological WHERE clauses', () => {
      const queries = [
        'DELETE FROM users WHERE 1=1;',
        'DELETE FROM users WHERE 0=0;',
        "DELETE FROM users WHERE 'a'='a';",
        "DELETE FROM users WHERE '1'='1';",
        'DELETE FROM users WHERE true;',
        'DELETE FROM users WHERE 1;',
        'DELETE FROM users WHERE null is null;',
        'DELETE FROM users WHERE 1 <= 1;',
      ];

      for (const q of queries) {
        const audit = auditSqlQuery(q, 'guarded-write');
        assert.equal(audit.allowed, false, `Expected tautology to be blocked: ${q}`);
        assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
      }
    });

    test('should strictly block unbounded UPDATE without WHERE clause', () => {
      const q = "UPDATE users SET status = 'disabled';";
      const audit = auditSqlQuery(q, 'guarded-write');
      assert.equal(audit.allowed, false);
      assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
    });

    test('should strictly block UPDATE with tautological WHERE clause', () => {
      const q = "UPDATE users SET status = 'disabled' WHERE 1=1;";
      const audit = auditSqlQuery(q, 'guarded-write');
      assert.equal(audit.allowed, false);
      assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
    });
  });

  describe('Multi-Statement & Chained Injection Defense', () => {
    test('should block multi-statement query if any statement is destructive', () => {
      const q = 'SELECT * FROM users; DROP TABLE accounts;';
      const audit = auditSqlQuery(q, 'guarded-write');
      assert.equal(audit.allowed, false);
      assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
      assert(audit.violations.some((v) => v.includes('[Statement 2]')));
    });

    test('should block multi-statement query with hidden unbounded delete', () => {
      const q = "SELECT 1; UPDATE config SET val='x' WHERE id=1; DELETE FROM audit_log;";
      const audit = auditSqlQuery(q, 'guarded-write');
      assert.equal(audit.allowed, false);
      assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
    });
  });

  describe('Read-Only Policy Enforcement', () => {
    test('should allow safe SELECT queries in read-only mode', () => {
      const queries = [
        'SELECT id, name, email FROM users WHERE id = 42;',
        'SELECT count(*) FROM orders;',
        'WITH active AS (SELECT id FROM users WHERE active = 1) SELECT * FROM active;',
        'EXPLAIN SELECT * FROM users;',
      ];

      for (const q of queries) {
        const audit = auditSqlQuery(q, 'read-only');
        assert.equal(audit.allowed, true, `Expected safe query to be allowed: ${q}`);
        assert.equal(audit.riskLevel, 'SAFE');
      }
    });

    test('should reject mutation queries in read-only mode even if bounded', () => {
      const q = "INSERT INTO users (id, name) VALUES (1, 'Alice');";
      const audit = auditSqlQuery(q, 'read-only');
      assert.equal(audit.allowed, false);
      assert.equal(audit.riskLevel, 'MEDIUM');
      assert(audit.violations[0].includes("'read-only' mode"));
    });

    test('should allow bounded mutations only in guarded-write mode', () => {
      const q = 'DELETE FROM users WHERE id = 123;';
      const audit = auditSqlQuery(q, 'guarded-write');
      assert.equal(audit.allowed, true);
      assert.equal(audit.riskLevel, 'LOW');
    });
  });

  describe('MongoDB Guardrails', () => {
    test('should block dropDatabase and dropCollection', () => {
      const queries = [
        'db.users.drop()',
        '{"operation": "drop", "collection": "users"}',
        '{"operation": "dropDatabase"}',
      ];

      for (const q of queries) {
        const audit = auditMongoQuery(q, 'guarded-write');
        assert.equal(audit.allowed, false);
        assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
      }
    });

    test('should block deleteMany with empty filter', () => {
      const queries = [
        'db.users.deleteMany({})',
        '{"operation": "deleteMany", "collection": "users", "filter": {}}',
      ];

      for (const q of queries) {
        const audit = auditMongoQuery(q, 'guarded-write');
        assert.equal(audit.allowed, false);
        assert.equal(audit.riskLevel, 'CRITICAL_BLOCKED');
      }
    });

    test('should allow bounded find and updateOne in MongoDB', () => {
      const findCmd = '{"operation": "find", "collection": "users", "filter": {"status": "active"}}';
      const auditFind = auditMongoQuery(findCmd, 'read-only');
      assert.equal(auditFind.allowed, true);

      const updateCmd = '{"operation": "updateOne", "collection": "users", "filter": {"id": 10}, "update": {"$set": {"active": false}}}';
      const auditUpdate = auditMongoQuery(updateCmd, 'guarded-write');
      assert.equal(auditUpdate.allowed, true);
    });
  });
});
