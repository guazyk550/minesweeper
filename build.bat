@echo off
rem 编译 + 打包成一个可双击运行的 jar
setlocal enabledelayedexpansion
set DIR=%~dp0
set SRC=%DIR%src
set OUT=%DIR%out

set JAVAC=javac
set JARTOOL=jar
where javac >nul 2>nul || set JAVAC=C:\Program Files\Java\jdk-24\bin\javac.exe
where jar   >nul 2>nul || set JARTOOL=C:\Program Files\Java\jdk-24\bin\jar.exe

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
dir /s /b "%SRC%\*.java" > "%DIR%sources.txt"
"%JAVAC%" -encoding UTF-8 -d "%OUT%" @"%DIR%sources.txt"
if errorlevel 1 goto fail
"%JARTOOL%" --create --file "%DIR%minesweeper.jar" --main-class minesweeper.MainFrame -C "%OUT%" .
if errorlevel 1 goto fail
del "%DIR%sources.txt"
echo.
echo   编译打包完成: %DIR%minesweeper.jar
echo   双击 run.bat 即可运行
echo.
goto end
:fail
echo.
echo   编译失败：请确认已安装 JDK（javac 在 PATH 中，或装在 C:\Program Files\Java\jdk-24）
echo.
:end
endlocal
