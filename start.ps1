$ErrorActionPreference = 'Stop'
$python = $null
$astral = Join-Path $env:APPDATA 'uv\python'
if (Test-Path $astral) {
    $candidate = Get-ChildItem $astral -Directory | Where-Object { $_.Name -match '^cpython-3\.(1[0-3])-.*windows' } | Sort-Object Name -Descending | Select-Object -First 1
    if ($candidate) { $python = Join-Path $candidate.FullName 'python.exe' }
}
if (-not $python) {
    foreach ($version in @('3.13', '3.12', '3.11', '3.10')) {
        try {
            $path = & py "-$version" -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $path) { $python = $path; break }
        } catch { continue }
    }
}
if (-not $python) { throw 'Cần cài Python 3.10–3.13 có tkinter.' }
& $python (Join-Path $PSScriptRoot 'launcher\app.py')
