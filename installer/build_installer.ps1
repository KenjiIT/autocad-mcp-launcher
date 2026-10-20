$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content -LiteralPath (Join-Path $root 'VERSION') -Raw).Trim()
$archive = Join-Path $root 'dist\autocad-mcp-launcher-complete.zip'
$stage = Join-Path $root 'dist\installer-payload'
$sourceRoot = Join-Path $stage 'autocad-mcp-launcher'
$compiler = $env:INNO_SETUP_COMPILER
if (-not $compiler) {
    $compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
}

if (-not (Test-Path -LiteralPath $archive)) {
    throw "Portable package not found: $archive. Run scripts/build_portable.py first."
}
if (-not (Test-Path -LiteralPath $compiler)) {
    throw "Inno Setup 6 compiler not found: $compiler"
}

if (Test-Path -LiteralPath $stage) {
    $distRoot = [IO.Path]::GetFullPath((Join-Path $root 'dist'))
    $stageFullPath = [IO.Path]::GetFullPath($stage)
    if (-not $stageFullPath.StartsWith($distRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove staging path outside dist: $stageFullPath"
    }
    Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Path $stage | Out-Null
Expand-Archive -LiteralPath $archive -DestinationPath $stage -Force

$installerScript = Join-Path $root 'installer\AutoCADMcpLauncher.iss'
Push-Location $root
try {
    & $compiler "/DAppVersion=$version" "/DSourceRoot=$sourceRoot" $installerScript
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE"
}

$output = Join-Path $root "dist\AutoCAD-MCP-Launcher-Setup-$version.exe"
if (-not (Test-Path -LiteralPath $output)) {
    throw "Installer output was not created: $output"
}
Write-Output $output
