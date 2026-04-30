# Save query 976552 result（脚本在 code/，数据在项目根 data/）
$projectRoot = Split-Path $PSScriptRoot -Parent
$json = Get-Content -Raw (Join-Path $projectRoot "data\_full_976552.json")
$saveStdin = Join-Path $PSScriptRoot "save_stdin.py"
$json | python $saveStdin