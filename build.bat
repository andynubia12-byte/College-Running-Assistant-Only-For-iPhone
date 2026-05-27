@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   GeoPilot Build Script
echo ============================================

:: ---- 1. PyInstaller ----
echo.
echo [1/3] Building with PyInstaller...
pyinstaller geosim.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)
echo Done: dist\GeoPilot\

:: ---- 2. Portable ZIP ----
echo.
echo [2/3] Creating portable ZIP...
powershell -Command "Compress-Archive -Path dist\GeoPilot\* -DestinationPath dist\GeoPilot_portable.zip -Force"
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: ZIP creation failed
) else (
    echo Done: dist\GeoPilot_portable.zip
)

:: ---- 3. SFX installer (WinRAR) ----
echo.
echo [3/3] SFX installer...
where rar >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where winrar >nul 2>&1
)
if %ERRORLEVEL% NEQ 0 (
    echo SKIP: WinRAR not found. SFX installer not created.
    echo Install WinRAR and re-run, or use the portable ZIP.
) else (
    :: Find WinRAR
    for /f "delims=" %%i in ('where rar 2^>nul') do set RAR=%%i
    if not defined RAR (
        for /f "delims=" %%i in ('where winrar 2^>nul') do set RAR=%%i
    )

    if exist installer\sfx.conf (
        "!RAR!" a -sfx -z"installer\sfx.conf" dist\GeoPilot_setup.exe dist\GeoPilot\*
        if !ERRORLEVEL! EQU 0 (
            echo Done: dist\GeoPilot_setup.exe
        ) else (
            echo WARNING: SFX creation failed
        )
    ) else (
        echo SKIP: installer\sfx.conf not found
    )
)

echo.
echo ============================================
echo   Build complete
echo   dist\GeoPilot\           -- onedir (for debugging)
echo   dist\GeoPilot_portable.zip -- portable
echo   dist\GeoPilot_setup.exe    -- installer ^(if WinRAR available^)
echo ============================================
