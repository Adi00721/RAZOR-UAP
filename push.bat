@echo off
setlocal
cd /d "%~dp0"
set "PATH=C:\Users\4321a\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd;%PATH%"

echo ============================================================
echo   RazorUAP - Push to GitHub Repository
echo   Target: https://github.com/Adi00721/RAZOR-UAP.git
echo ============================================================
echo.

git push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo [!] If prompted for a password, enter your GitHub Personal Access Token (PAT) with 'repo' scope.
    echo Create a token here: https://github.com/settings/tokens
)

pause
