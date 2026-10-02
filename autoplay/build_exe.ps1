# 把扫雷自动玩打包成一个独立 exe（不需要目标机器装 Python）
#
# 用法（在本 autoplay 目录下）：
#   powershell -ExecutionPolicy Bypass -File build_exe.ps1
#
# 产物：dist\MinesweeperAutoPlay.exe
#   · 内置 Python + numpy + Pillow
#   · 可以放到任何目录、任何机器上双击运行
#   · 日志 / 胜利截图写在 exe 自己所在的目录

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$py = "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host "==> 检查 PyInstaller" -ForegroundColor Cyan
& $py -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "    未安装，正在安装 …" -ForegroundColor Yellow
    $env:HTTP_PROXY = 'http://127.0.0.1:7897'
    $env:HTTPS_PROXY = 'http://127.0.0.1:7897'
    & $py -m pip install --quiet pyinstaller
}

$icon = Join-Path $here "..\packaging\minesweeper.ico"
if (-not (Test-Path $icon)) { $icon = "" }

Write-Host "==> 打包中（约 1 分钟）" -ForegroundColor Cyan
Set-Location $here
& $py -m PyInstaller --noconfirm --onefile --console `
    --name MinesweeperAutoPlay `
    --distpath (Join-Path $here "dist") `
    --workpath (Join-Path $here "build_pyi") `
    --specpath (Join-Path $here "build_pyi") `
    $(if ($icon) { "--icon"; $icon } else { }) `
    (Join-Path $here "autoplay.py")

$exe = Join-Path $here "dist\MinesweeperAutoPlay.exe"
if (Test-Path $exe) {
    $mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "==> 完成：$exe  ($mb MB)" -ForegroundColor Green
    Write-Host "    这个 exe 可以直接拷到任何地方双击运行，不需要装 Python。" -ForegroundColor Green
} else {
    Write-Host "打包失败" -ForegroundColor Red
}
