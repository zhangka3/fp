param(
    [string]$QueryId,
    [string]$JsonFile
)

# Read JSON from file and pipe to Python
$saveStdin = Join-Path $PSScriptRoot "save_stdin.py"
Get-Content -Raw $JsonFile | python $saveStdin