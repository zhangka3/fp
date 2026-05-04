# 一次性启用仓库内 hooks：推送前自动 git add -A（见 .githooks/pre-push）
$ErrorActionPreference = "Stop"
$root = git rev-parse --show-toplevel 2>$null
if (-not $root) { Write-Error "请在仓库根目录执行"; exit 1 }
Set-Location $root
git config core.hooksPath .githooks
Write-Host "[OK] core.hooksPath=.githooks"
Write-Host "     每次 git push 会先 git add -A；若有未提交变更会阻止 push 并提示先 commit"
