# PowerShell Security & Hardening Guide

Staff-level guide to script security, credential protection, and defense against code injection in PowerShell, cross-referencing [`api-security`](file:///.github/skills/api-security/SKILL.md).

---

## 1. Zero-Tolerance `Invoke-Expression` (`iex`) Ban

- [ ] **Never Use `Invoke-Expression` (`iex`)**:
  - `Invoke-Expression` treats any input string as arbitrary executable code. If the string contains any user-controlled input, parameters, or file content, it creates an immediate **Remote Code Execution (RCE) / Arbitrary Command Injection** vulnerability.
  - Flag any use of `Invoke-Expression` or `iex` as `[P0 - Blocker]`.

```powershell
# TERRIBLE / DANGEROUS:
$userSuppliedPath = "C:\safe; Remove-Item -Path C:\Important -Recurse"
Invoke-Expression "Get-ChildItem -Path $userSuppliedPath" # Executes the deletion!

# SAFE: Call operator with parameter binding
$safePath = "C:\safe"
& Get-ChildItem -Path $safePath
```

---

## 2. Credential & Secret Management

- [ ] **No Hardcoded Plaintext Secrets**:
  - Never store passwords, API keys, or access tokens as plaintext strings in scripts or manifests. Flag as `[P0 - Blocker]`.
- [ ] **Accepting Credentials in Cmdlets**:
  - Use `[pscredential]` parameter type, which automatically handles secure password storage in RAM:
  ```powershell
  param(
      [Parameter(Mandatory = $true)]
      [pscredential]$Credential
  )
  ```
- [ ] **Microsoft.PowerShell.SecretManagement**:
  - For cross-platform script automation that must retrieve secrets from Azure Key Vault, HashiCorp Vault, or local credential lockers, use `Get-Secret`:
  ```powershell
  # Retrieve from registered secret vault
  $apiKey = Get-Secret -Name 'Production-ApiKey' -AsPlainText
  ```

---

## 3. Execution Policy Scoping

Execution policies are safety rails, not a security boundary (they prevent accidental execution, not malicious bypass).
- In automated scripts or CI/CD jobs, run scripts with:
  ```powershell
  pwsh -NoProfile -ExecutionPolicy Bypass -File ./deploy.ps1
  ```
- Inside a running session, set the policy strictly for the current process:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
  ```

---

## 4. Constrained Language Mode (CLM) & Script Block Logging

In enterprise environments with AppLocker or Windows Defender Application Control (WDAC), PowerShell runs in **Constrained Language Mode (CLM)**:
- CLM blocks direct .NET reflection, `Add-Type` compilation, and raw COM objects.
- Write scripts using native cmdlets and approved .NET types (`[System.DateTime]`, `[System.Uri]`, `[math]`) rather than arbitrary C# reflection to ensure compatibility with CLM.
- Be aware that **Script Block Logging (Event ID 4104)** captures the full text of all script blocks executed. Do not embed plaintext passwords in parameters or inline scripts.
