/**
 * Facade module re-exporting tools, process, and security components
 */
export { executeCode } from './tools/execute-code.js';
export { evaluateExpression } from './tools/evaluate-expr.js';
export { executeFile } from './tools/execute-file.js';
export { runPackageScript } from './tools/package-script.js';
export { getRuntimeInfo } from './tools/runtime-info.js';
export { supportsNativeTypeScript, supportsPermissionModel, getPermissionFlags } from './security/permissions.js';
export { sanitizeEnvironment } from './security/sanitizer.js';
export { preExecutionSecurityCheck } from './security/validator.js';
export { runProcess } from './process/runner.js';
export { terminateProcess } from './process/terminator.js';
export * from './types.js';
