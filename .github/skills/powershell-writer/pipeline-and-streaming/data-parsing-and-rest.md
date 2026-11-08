# PowerShell Data Parsing, REST APIs & Native CLI

Audit and implementation guide for structured data formats (JSON, CSV, XML), RESTful APIs, and native CLI interop.

---

## 1. REST APIs (`Invoke-RestMethod` vs. `Invoke-WebRequest`)

- **`Invoke-RestMethod` (`irm`)**: Automatically deserializes JSON, XML, or RSS responses into native PowerShell objects or hashtables. Use for API automation.
- **`Invoke-WebRequest` (`iwr`)**: Returns the raw HTTP response object with headers, status codes, and raw content. Use when inspecting HTTP response headers or downloading raw files (`-OutFile`).

### Robust API Invocation Pattern
```powershell
function Invoke-AuthenticatedApi {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Endpoint,

        [Parameter(Mandatory = $true)]
        [string]$AuthToken,

        [Parameter()]
        [hashtable]$QueryParameters = @{}
    )

    $baseUrl = 'https://api.enterprise.com/v1'
    $uriBuilder = [System.UriBuilder]::new("$baseUrl/$Endpoint")

    if ($QueryParameters.Count -gt 0) {
        $queryString = ($QueryParameters.GetEnumerator() | ForEach-Object {
            "$([System.Uri]::EscapeDataString($_.Key))=$([System.Uri]::EscapeDataString($_.Value))"
        }) -join '&'
        $uriBuilder.Query = $queryString
    }

    $headers = @{
        'Authorization' = "Bearer $AuthToken"
        'Accept'        = 'application/json'
        'User-Agent'    = 'PowerShell-Automation/2.0'
    }

    try {
        $response = Invoke-RestMethod -Uri $uriBuilder.Uri `
                                      -Method Get `
                                      -Headers $headers `
                                      -TimeoutSec 15 `
                                      -ErrorAction Stop
        return $response
    }
    catch {
        Write-Error "API call failed for $($uriBuilder.Uri): $($_.Exception.Message)"
        throw
    }
}
```

---

## 2. JSON Serialization & Deserialization

### The Depth Trap in `ConvertTo-Json`
By default in Windows PowerShell 5.1 and earlier PowerShell 7, `ConvertTo-Json` truncates nested objects at **depth 2**!
- Any properties deeper than level 2 are replaced by string representations like `"System.Collections.Hashtable"`.
- **Always specify `-Depth 10` (or higher)** when serializing complex or nested objects:
```powershell
$jsonPayload = $complexObject | ConvertTo-Json -Depth 10 -Compress
```

### `ConvertFrom-Json` with `-AsHashtable`
In PowerShell 6+, parsing JSON with `-AsHashtable` creates standard ordered hashtables instead of PSCustomObjects, which allows faster dictionary lookups and case-sensitive key matching when needed:
```powershell
$config = Get-Content -Raw -Path 'config.json' | ConvertFrom-Json -AsHashtable
```

---

## 3. CSV & Delimited Text

```powershell
# Import with custom headers or delimiter
$records = Import-Csv -Path 'data.tsv' -Delimiter "`t"

# Export clean CSV (always use -NoTypeInformation in PS 5.1; default in PS 7)
$records |
    Select-Object Id, Username, Email, CreatedDate |
    Export-Csv -Path 'export.csv' -NoTypeInformation -Encoding utf8
```

---

## 4. Invoking Native CLI Tools Safely

PowerShell's parser can distort command-line arguments containing quotes, spaces, or slashes when calling native binaries (`git`, `docker`, `az`, `kubectl`).

### Best Practices for Native CLIs:
1. **Pass Arguments as an Array**:
   ```powershell
   $dockerArgs = @('run', '-d', '--name', 'test-redis', '-p', '6379:6379', 'redis:alpine')
   & docker @dockerArgs
   ```
2. **Stop-Parsing Symbol (`--%`)**:
   Tells PowerShell to treat all subsequent text as literal command line tokens without expanding variables or quotes:
   ```powershell
   & az group create --% -n "rg-prod-01" --location "eastus2" --tags "env=prod"
   ```
3. **Always Check `$LASTEXITCODE`**:
   ```powershell
   & npm test
   if ($LASTEXITCODE -ne 0) {
       throw "npm test failed with exit code $LASTEXITCODE"
   }
   ```

