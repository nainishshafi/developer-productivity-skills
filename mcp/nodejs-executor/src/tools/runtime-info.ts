import * as os from 'node:os';
import { supportsNativeTypeScript, supportsPermissionModel } from '../security/permissions.js';
import type { RuntimeInfo } from '../types.js';

export function getRuntimeInfo(): RuntimeInfo {
  const mem = process.memoryUsage();
  return {
    nodeVersion: process.version,
    v8Version: process.versions.v8,
    platform: process.platform,
    architecture: process.arch,
    osRelease: os.release(),
    cpuCount: os.cpus().length,
    memoryUsageMb: {
      rss: Math.round(mem.rss / (1024 * 1024) * 100) / 100,
      heapTotal: Math.round(mem.heapTotal / (1024 * 1024) * 100) / 100,
      heapUsed: Math.round(mem.heapUsed / (1024 * 1024) * 100) / 100,
      external: Math.round(mem.external / (1024 * 1024) * 100) / 100,
    },
    uptimeSeconds: Math.round(process.uptime()),
    workingDirectory: process.cwd(),
    execPath: process.execPath,
    typescriptNativeSupport: supportsNativeTypeScript(),
    permissionModelSupport: supportsPermissionModel(),
  };
}

