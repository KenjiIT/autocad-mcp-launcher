param(
    [string]$AutoCADDir = $env:AUTOCAD_MCP_AUTOCAD_DIR,
    [string]$DotNet = "dotnet",
    [string]$CertificateThumbprint,
    [string]$SignTool = "signtool.exe",
    [switch]$Install,
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"
$nativeRoot = Split-Path -Parent $PSScriptRoot
$project = Join-Path $nativeRoot "AutoCADMcp.Plugin\AutoCADMcp.Plugin.csproj"
$manifest = Join-Path $nativeRoot "AutoCADMcp.bundle\PackageContents.xml"
$artifactRoot = Join-Path $nativeRoot "artifacts\AutoCADMcp.bundle"
$contentRoot = Join-Path $artifactRoot "Contents\Windows"

if (-not $AutoCADDir -or -not (Test-Path -LiteralPath (Join-Path $AutoCADDir "AcMgd.dll"))) {
    throw "AutoCADDir must point to an AutoCAD 2025, 2026, or 2027 installation."
}

$acadExe = Join-Path $AutoCADDir "acad.exe"
$versionText = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($acadExe).ProductVersion
if (-not $versionText) {
    $versionText = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($acadExe).FileVersion
}
$releaseMatch = [regex]::Match($versionText, '\d+\.\d+')
if (-not $releaseMatch.Success) {
    throw "Could not parse AutoCAD API release from version '$versionText'."
}
$release = $releaseMatch.Value
$releaseConfig = switch ($release) {
    "25.0" { @{ Year = 2025; Series = "R25.0"; Framework = "net8.0-windows" } }
    "25.1" { @{ Year = 2026; Series = "R25.1"; Framework = "net8.0-windows" } }
    "26.0" { @{ Year = 2027; Series = "R26.0"; Framework = "net10.0-windows" } }
    default { throw "Unsupported AutoCAD API release '$release' (version '$versionText')." }
}

$env:AUTOCAD_MCP_AUTOCAD_DIR = $AutoCADDir
& $DotNet restore $project `
    "-p:AutoCADDir=$AutoCADDir" "-p:TargetFramework=$($releaseConfig.Framework)"
if ($LASTEXITCODE -ne 0) {
    throw "Native plugin restore failed with exit code $LASTEXITCODE."
}
& $DotNet build $project -c $Configuration --no-restore --nologo `
    "-p:AutoCADDir=$AutoCADDir" "-p:TargetFramework=$($releaseConfig.Framework)"
if ($LASTEXITCODE -ne 0) {
    throw "Native plugin build failed with exit code $LASTEXITCODE."
}

New-Item -ItemType Directory -Force -Path $contentRoot | Out-Null
$manifestText = Get-Content -LiteralPath $manifest -Raw
$manifestText = $manifestText -replace 'SeriesMin="[^"]+"', "SeriesMin=`"$($releaseConfig.Series)`""
$manifestText = $manifestText -replace 'SeriesMax="[^"]+"', "SeriesMax=`"$($releaseConfig.Series)`""
Set-Content -LiteralPath (Join-Path $artifactRoot "PackageContents.xml") `
    -Value $manifestText -Encoding utf8
$assembly = Join-Path $nativeRoot "AutoCADMcp.Plugin\bin\$Configuration\$($releaseConfig.Framework)\AutoCADMcp.Plugin.dll"
$packagedAssembly = Join-Path $contentRoot "AutoCADMcp.Plugin.dll"
Copy-Item -LiteralPath $assembly -Destination $packagedAssembly -Force

if ($CertificateThumbprint) {
    & $SignTool sign /sha1 $CertificateThumbprint /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $packagedAssembly
    if ($LASTEXITCODE -ne 0) {
        throw "Authenticode signing failed with exit code $LASTEXITCODE."
    }
    & $SignTool verify /pa $packagedAssembly
    if ($LASTEXITCODE -ne 0) {
        throw "The packaged native plugin did not pass Authenticode verification."
    }
}

$installedBundle = $null
if ($Install) {
    if (-not $CertificateThumbprint) {
        throw "-Install requires -CertificateThumbprint; SECURELOAD must remain enabled."
    }
    $applicationPlugins = Join-Path $env:APPDATA "Autodesk\ApplicationPlugins"
    $installedBundle = Join-Path $applicationPlugins "AutoCADMcp.bundle"
    New-Item -ItemType Directory -Force -Path $applicationPlugins | Out-Null
    $resolvedPlugins = [System.IO.Path]::GetFullPath($applicationPlugins).TrimEnd('\')
    $resolvedBundle = [System.IO.Path]::GetFullPath($installedBundle)
    if (-not $resolvedBundle.StartsWith($resolvedPlugins + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to replace a bundle outside the Autodesk ApplicationPlugins directory: $resolvedBundle"
    }
    if (Test-Path -LiteralPath $installedBundle) {
        Remove-Item -LiteralPath $installedBundle -Recurse -Force
    }
    Copy-Item -LiteralPath $artifactRoot -Destination $installedBundle -Recurse -Force
}

[pscustomobject]@{
    Bundle = $artifactRoot
    Assembly = $packagedAssembly
    Signed = [bool]$CertificateThumbprint
    InstalledBundle = $installedBundle
    AutoCADDir = (Resolve-Path -LiteralPath $AutoCADDir).Path
    AutoCADYear = $releaseConfig.Year
    TargetFramework = $releaseConfig.Framework
    Configuration = $Configuration
}
