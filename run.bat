@echo off
rem 扫雷 Minesweeper —— 双击即可运行（需要 JDK 8+，本机已装 JDK 24）
setlocal
set DIR=%~dp0
if exist "%DIR%minesweeper.jar" (
  start "" javaw -jar "%DIR%minesweeper.jar" %*
) else (
  start "" javaw -cp "%DIR%out" minesweeper.MainFrame %*
)
endlocal
