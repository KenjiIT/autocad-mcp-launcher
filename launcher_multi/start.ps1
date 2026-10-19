$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$app = Join-Path $PSScriptRoot 'app.py'
$python = Join-Path $root 'autocad-beiming-mcp-custom\.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path $root 'autocad-beiming-mcp-custom\.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $python)) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show('Chưa cài môi trường Beiming. Hãy khởi chạy launcher hiện tại một lần để cài thư viện trước.', 'Multi-Session Launcher') | Out-Null
    exit 1
}
Start-Process -FilePath $python -ArgumentList @('"' + $app + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
