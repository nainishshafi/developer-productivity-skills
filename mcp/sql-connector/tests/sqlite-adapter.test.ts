import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { SqliteAdapter } from '../dist/adapters/sqlite-adapter.js';

describe('SQLite Adapter & Guardrails Integration', () => {
  let adapter: SqliteAdapter;

  before(async () => {
    adapter = new SqliteAdapter({ engine: 'sqlite', filePath: ':memory:' });
    await adapter.connect();

    // Setup table schema
    await adapter.query({
      query: `
        CREATE TABLE products (
          id INTEGER PRIMARY KEY,
          sku TEXT NOT NULL,
          price REAL NOT NULL,
          inventory INTEGER NOT NULL
        );
      `,
      mode: 'guarded-write',
    });

    // Populate seed records
    for (let i = 1; i <= 20; i++) {
      await adapter.query({
        query: `INSERT INTO products (id, sku, price, inventory) VALUES (${i}, 'SKU-${i}', ${i * 10.5}, ${i * 5});`,
        mode: 'guarded-write',
      });
    }
  });

  after(async () => {
    await adapter.disconnect();
  });

  test('should execute read-only query and return formatted rows', async () => {
    const res = await adapter.query({
      query: 'SELECT * FROM products WHERE price > 50 ORDER BY id ASC;',
      mode: 'read-only',
    });

    assert.equal(res.success, true);
    assert.equal(res.engine, 'sqlite');
    assert.equal(res.mode, 'read-only');
    assert(res.rowCount! > 0);
    assert.deepEqual(res.columns, ['id', 'sku', 'price', 'inventory']);
  });

  test('should enforce maxRows truncation guardrail', async () => {
    const res = await adapter.query({
      query: 'SELECT * FROM products;',
      mode: 'read-only',
      maxRows: 5,
    });

    assert.equal(res.success, true);
    assert.equal(res.rowCount, 5);
    assert.equal(res.truncated, true);
  });

  test('should list tables and views', async () => {
    const tables = await adapter.listTables();
    assert(tables.some((t) => t.name === 'products'));
  });

  test('should describe table schema accurately', async () => {
    const cols = await adapter.describeTable('products');
    assert.equal(cols.length, 4);

    const idCol = cols.find((c) => c.name === 'id');
    assert(idCol);
    assert.equal(idCol.isPrimaryKey, true);

    const skuCol = cols.find((c) => c.name === 'sku');
    assert(skuCol);
    assert.equal(skuCol.nullable, false);
  });

  test('should strictly block DROP TABLE via adapter query', async () => {
    const res = await adapter.query({
      query: 'DROP TABLE products;',
      mode: 'guarded-write',
    });

    assert.equal(res.success, false);
    assert(res.error?.includes('SQL Firewall blocked execution'));
    assert(res.error?.includes('DROP TABLE'));

    // Verify products table was NOT dropped
    const checkRes = await adapter.query({
      query: 'SELECT count(*) as count FROM products;',
      mode: 'read-only',
    });
    assert.equal(checkRes.success, true);
  });

  test('should strictly block DELETE without WHERE clause', async () => {
    const res = await adapter.query({
      query: 'DELETE FROM products;',
      mode: 'guarded-write',
    });

    assert.equal(res.success, false);
    assert(res.error?.includes('Unbounded'));

    // Verify data is still intact
    const countRes = await adapter.query({
      query: 'SELECT count(*) as count FROM products;',
      mode: 'read-only',
    });
    assert.equal((countRes.rows?.[0] as any).count, 20);
  });

  test('should execute EXPLAIN QUERY PLAN safely', async () => {
    const explainRes = await adapter.explain("SELECT * FROM products WHERE sku = 'SKU-1'");
    assert.equal(explainRes.engine, 'sqlite');
    assert(explainRes.rawText?.length! > 0);
  });
});

describe('AdapterFactory Connection Pool & LRU Eviction', () => {
  test('should reuse connected adapter for identical connection config', async () => {
    const { AdapterFactory } = await import('../dist/adapters/adapter-factory.js');
    const config1 = { engine: 'sqlite' as const, filePath: ':memory:' };
    const a1 = await AdapterFactory.getAdapter(config1);
    const a2 = await AdapterFactory.getAdapter(config1);

    assert.equal(a1, a2);
    await AdapterFactory.closeAll();
    assert.equal(AdapterFactory.getPoolSize(), 0);
  });

  test('should track pool size and allow idle eviction', async () => {
    const { AdapterFactory } = await import('../dist/adapters/adapter-factory.js');
    await AdapterFactory.closeAll();

    const config = { engine: 'sqlite' as const, filePath: ':memory:' };
    await AdapterFactory.getAdapter(config);
    assert.equal(AdapterFactory.getPoolSize(), 1);

    // Evict with 0ms max idle
    const evicted = await AdapterFactory.evictIdle(0);
    assert.equal(evicted, 1);
    assert.equal(AdapterFactory.getPoolSize(), 0);
  });
});

describe('Timeout Utility Boundary', () => {
  test('should reject when operation exceeds timeout boundary', async () => {
    const { withTimeout } = await import('../dist/utils.js');
    const hangingPromise = new Promise((resolve) => setTimeout(resolve, 500));

    await assert.rejects(
      async () => {
        await withTimeout(hangingPromise, 50, 'Test operation');
      },
      /Test operation timed out after 50ms/
    );
  });

  test('should resolve cleanly within timeout boundary', async () => {
    const { withTimeout } = await import('../dist/utils.js');
    const fastPromise = Promise.resolve('ok');
    const res = await withTimeout(fastPromise, 500);
    assert.equal(res, 'ok');
  });
});
