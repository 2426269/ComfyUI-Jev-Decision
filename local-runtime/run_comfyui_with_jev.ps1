param(
    [switch] $ValidateOnly,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ExtraArguments
)

$ErrorActionPreference = 'Stop'
$envFile = Join-Path $PSScriptRoot '.env.local'
$projectRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $projectRoot
$comfyRoot = Join-Path $workspaceRoot 'ComfyUI-NAI'
$python = Join-Path $comfyRoot '.venv\Scripts\python.exe'
$main = Join-Path $comfyRoot 'main.py'
$outputDirectory = Join-Path $workspaceRoot 'SmartGallery-Archive\NAI'

if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
    throw "Missing local credential file: $envFile"
}

$apiKey = ''
foreach ($rawLine in Get-Content -LiteralPath $envFile) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith('#')) {
        continue
    }
    $parts = $line -split '=', 2
    if ($parts.Count -eq 2 -and $parts[0].Trim() -eq 'TYPESAFE_API_KEY') {
        $apiKey = $parts[1].Trim()
        break
    }
}

if (-not $apiKey) {
    throw 'TYPESAFE_API_KEY is empty in local-runtime/.env.local'
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "ComfyUI Python was not found: $python"
}
if (-not (Test-Path -LiteralPath $main -PathType Leaf)) {
    throw "ComfyUI main.py was not found: $main"
}

$env:TYPESAFE_API_KEY = $apiKey
$env:PYTHONUTF8 = '1'

if ($ValidateOnly) {
    [pscustomobject]@{
        CredentialConfigured = $true
        ComfyRoot = $comfyRoot
        PythonFound = $true
        MainFound = $true
        PluginLinkFound = (Test-Path -LiteralPath (Join-Path $comfyRoot 'custom_nodes\ComfyUI-Jev-Decision'))
    } | ConvertTo-Json -Compress
    Remove-Item Env:TYPESAFE_API_KEY -ErrorAction SilentlyContinue
    exit 0
}

$arguments = @(
    $main,
    '--cpu',
    '--listen', '0.0.0.0',
    '--port', '8188',
    '--output-directory', $outputDirectory,
    '--auto-launch'
) + $ExtraArguments

Push-Location -LiteralPath $comfyRoot
try {
    & $python @arguments
    exit $LASTEXITCODE
}
finally {
    Remove-Item Env:TYPESAFE_API_KEY -ErrorAction SilentlyContinue
    Pop-Location
}
