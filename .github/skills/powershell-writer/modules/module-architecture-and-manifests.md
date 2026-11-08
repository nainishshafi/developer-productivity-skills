# PowerShell Module Architecture & Manifests

Staff-level guide to authoring, structuring, and publishing production PowerShell modules (`.psm1` / `.psd1`).

---

## 1. Professional Module Directory Structure

A clean, maintainable module separates public cmdlets from internal helper functions:

```
MyModule/
├── MyModule.psd1           # Module manifest (metadata, exported functions, GUID)
├── MyModule.psm1           # Root module loader script
├── Public/                 # Exported functions (one file per cmdlet)
│   ├── Get-MyResource.ps1
│   └── Set-MyResource.ps1
├── Private/                # Internal helper functions (not exported)
│   ├── Test-InternalAuth.ps1
│   └── Format-Payload.ps1
└── tests/                  # Pester unit and integration tests
    ├── MyModule.Tests.ps1
    └── Get-MyResource.Tests.ps1
```

---

## 2. The Module Root Loader (`.psm1`)

The `.psm1` dot-sources all private and public scripts dynamically:

```powershell
# MyModule.psm1
$publicScripts  = Get-ChildItem -Path "$PSScriptRoot/Public/*.ps1" -ErrorAction SilentlyContinue
$privateScripts = Get-ChildItem -Path "$PSScriptRoot/Private/*.ps1" -ErrorAction SilentlyContinue

# Dot-source all scripts into the module scope
foreach ($script in @($privateScripts; $publicScripts)) {
    try {
        . $script.FullName
    }
    catch {
        Write-Error "Failed to load script module file '$($script.FullName)': $_"
    }
}

# Export only public functions explicitly
if ($publicScripts) {
    Export-ModuleMember -Function $publicScripts.BaseName
}
```

---

## 3. Authoring the Module Manifest (`.psd1`)

Generate a manifest using `New-ModuleManifest` or author it directly:

```powershell
# MyModule.psd1
@{
    # Script module or binary module file associated with this manifest.
    RootModule = 'MyModule.psm1'

    # Version number of this module.
    ModuleVersion = '1.0.0'

    # Supported PSEditions
    CompatiblePSEditions = @('Core', 'Desktop')

    # ID used to uniquely identify this module
    GUID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'

    # Author and Company
    Author = 'Platform Engineering'
    CompanyName = 'Enterprise Automation'

    # Description of the functionality provided by this module
    Description = 'Enterprise utility module for data processing and infrastructure management.'

    # Minimum version of the PowerShell engine required by this module
    PowerShellVersion = '5.1'

    # Functions to export from this module (never use '*' in production!)
    FunctionsToExport = @(
        'Get-MyResource',
        'Set-MyResource'
    )

    # Cmdlets, Variables, and Aliases to export
    CmdletsToExport = @()
    VariablesToExport = @()
    AliasesToExport = @()

    # Private data for PSData repository publishing
    PrivateData = @{
        PSData = @{
            Tags = @('Automation', 'Cloud', 'CrossPlatform')
            ProjectUri = 'https://github.com/org/MyModule'
            LicenseUri = 'https://github.com/org/MyModule/blob/main/LICENSE'
        }
    }
}
```

### The Cardinal Rule of `FunctionsToExport`:
Never leave `FunctionsToExport = '*'` in production!
- Explicitly listing exported functions enables fast command discovery, module auto-loading, and tab completion without loading the full `.psm1` script into memory until invoked.

---

## 4. Validating the Manifest

Always validate manifests in CI/CD before releasing:

```powershell
# Validate syntax and export rules
$manifest = Test-ModuleManifest -Path './MyModule/MyModule.psd1'

if ($manifest) {
    Write-Host "Module manifest valid: $($manifest.Name) v$($manifest.Version)"
}
```

