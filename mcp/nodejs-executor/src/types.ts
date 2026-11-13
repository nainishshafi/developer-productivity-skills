export type SupportedLanguage = 'javascript' | 'typescript';

export type SandboxMode = 'strict' | 'workspace-write' | 'unrestricted';

export interface ExecuteCodeOptions {
  code: string;
  language?: SupportedLanguage;
  timeout?: number;
  workingDirectory?: string;
  environmentVariables?: Record<string, string>;
  sandboxMode?: SandboxMode;
  allowFsWritePaths?: string[];
}

export interface ExecuteFileOptions {
  filePath: string;
  args?: string[];
  timeout?: number;
  workingDirectory?: string;
  environmentVariables?: Record<string, string>;
  sandboxMode?: SandboxMode;
  allowFsWritePaths?: string[];
}

export interface EvaluateExpressionOptions {
  expression: string;
  timeout?: number;
  workingDirectory?: string;
  environmentVariables?: Record<string, string>;
  sandboxMode?: SandboxMode;
}

export interface RunPackageScriptOptions {
  script: string;
  packageManager?: 'npm' | 'pnpm' | 'yarn';
  projectPath?: string;
  args?: string[];
  timeout?: number;
}

export interface RunTerminalCommandOptions {
  command: string;
  args?: string[];
  workingDirectory?: string;
  environmentVariables?: Record<string, string>;
  timeout?: number;
}

export interface ExecutionResult {
  success: boolean;
  exitCode: number | null;
  stdout: string;
  stderr: string;
  durationMs: number;
  timedOut: boolean;
  error?: string;
  sandboxMode?: SandboxMode;
}

export interface ExpressionResult {
  success: boolean;
  type?: string;
  value?: string;
  stdout?: string;
  stderr?: string;
  durationMs: number;
  timedOut: boolean;
  error?: string;
  sandboxMode?: SandboxMode;
}

export interface RuntimeInfo {
  nodeVersion: string;
  v8Version: string;
  platform: string;
  architecture: string;
  osRelease: string;
  cpuCount: number;
  memoryUsageMb: {
    rss: number;
    heapTotal: number;
    heapUsed: number;
    external: number;
  };
  uptimeSeconds: number;
  workingDirectory: string;
  execPath: string;
  typescriptNativeSupport: boolean;
  permissionModelSupport: boolean;
}
