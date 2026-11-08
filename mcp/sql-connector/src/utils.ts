/**
 * Utility functions for SQL Connector MCP server
 */

/**
 * Wraps an async promise in a deterministic timeout boundary
 */
export function withTimeout<T = any>(
  promise: Promise<T>,
  timeoutMs: number = 15000,
  operationName: string = 'Database query'
): Promise<T> {
  let timer: NodeJS.Timeout;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(`${operationName} timed out after ${timeoutMs}ms.`));
    }, timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]).finally(() => {
    clearTimeout(timer);
  });
}
