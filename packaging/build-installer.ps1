<#
    打包 Windows 分发件：exe 安装程序 + 免安装版 zip

    依赖：
      - JDK 14+（本机 JDK 24），需要 jpackage
      - WiX Toolset v3（生成 exe/msi 安装程序用），本机装在
        C:\Program Files (x86)\WiX Toolset v3.14\bin

    用法（在仓库根目录）：
      powershell -ExecutionPolicy Bypass -File packaging\build-installer.ps1
      powershell -ExecutionPolicy Bypass -File packaging\build-installer.ps1 -Version 1.2.0
#>
param(
    [string]$Version = "1.1.0",
    [string]$JdkHome = "C:\Program Files\Java\jdk-24",
    [string]$WixBin = "C:\Program Files (x86)\WiX Toolset v3.14\bin"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot          # 仓库根目录
$build = Join-Path $root "build\packaging"
$input = Join-Path $build "input"
$dist = Join-Path $build "dist"
$icon = Join-Path $root "packaging\minesweeper.ico"
$jpackage = Join-Path $JdkHome "bin\jpackage.exe"

Write-Host "==> 清理并编译" -ForegroundColor Cyan
Remove-Item (Join-Path $root "build") -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $input, $dist | Out-Null

$out = Join-Path $root "out"
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null
& (Join-Path $JdkHome "bin\javac.exe") -encoding UTF-8 -d $out (Get-ChildItem (Join-Path $root "src\minesweeper\*.java")).FullName
if ($LASTEXITCODE -ne 0) { throw "编译失败" }

$jar = Join-Path $root "minesweeper.jar"
& (Join-Path $JdkHome "bin\jar.exe") --create --file $jar --main-class minesweeper.MainFrame -C $out .
if ($LASTEXITCODE -ne 0) { throw "打包 jar 失败" }
Copy-Item $jar $input -Force

if (-not (Test-Path (Join-Path $WixBin "candle.exe"))) {
    throw "找不到 WiX v3（$WixBin）。生成 exe 安装程序需要它：winget install WiXToolset.WiXToolset"
}
$env:PATH = "$WixBin;$env:PATH"

$common = @(
    "--name", "Minesweeper",
    "--app-version", $Version,
    "--input", $input,
    "--main-jar", "minesweeper.jar",
    "--main-class", "minesweeper.MainFrame",
    "--icon", $icon,
    "--description", "Classic Minesweeper with guaranteed-solvable boards and a built-in auto-player",
    "--vendor", "gua550",
    "--add-modules", "java.base,java.desktop,java.logging",
    "--jlink-options", "--compress=zip-6 --no-header-files --no-man-pages --strip-debug"
)

Write-Host "==> 生成免安装版 (app-image)" -ForegroundColor Cyan
& $jpackage --type app-image @common --dest $dist
if ($LASTEXITCODE -ne 0) { throw "app-image 生成失败" }

$appDir = Join-Path $dist "Minesweeper"
$zip = Join-Path $dist "Minesweeper-$Version-portable.zip"
Write-Host "==> 压缩免安装版 -> $zip" -ForegroundColor Cyan
Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $zip -CompressionLevel Optimal -Force

Write-Host "==> 生成 exe 安装程序" -ForegroundColor Cyan
& $jpackage --type exe @common --win-shortcut --win-menu --win-dir-chooser --dest $dist
if ($LASTEXITCODE -ne 0) { throw "exe 安装程序生成失败" }

Write-Host ""
Write-Host "==> 产物：" -ForegroundColor Green
Get-ChildItem $dist | Where-Object { $_.Name -notlike 'Minesweeper' } |
    Select-Object Name, @{n = '大小MB'; e = { [math]::Round($_.Length / 1MB, 1) } } |
    Format-Table -AutoSize
