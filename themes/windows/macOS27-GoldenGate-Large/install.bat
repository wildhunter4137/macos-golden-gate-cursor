@echo off
setlocal EnableExtensions
title macOS 27 Golden Gate Large cursors - one-click install

set "SRC=%~dp0"
set "DEST=%SystemRoot%\Cursors\macOS27-GoldenGate-Large"
set "SCHEME=macOS 27 Golden Gate Large"

rem Writing into %SystemRoot%\Cursors needs administrator rights.
rem If this window is not elevated, relaunch the script elevated.
whoami /groups | findstr /c:"S-1-16-12288" >nul 2>&1
if errorlevel 1 (
    echo Administrator rights are needed to copy the cursors into:
    echo   %DEST%
    echo A Windows prompt will ask you to confirm.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo [1/3] Copying cursors to %DEST% ...
if not exist "%DEST%" mkdir "%DEST%"
copy /y "%SRC%*.cur" "%DEST%\" >nul
copy /y "%SRC%*.ani" "%DEST%\" >nul

echo [2/3] Registering the "%SCHEME%" scheme ...
set "LIST=%DEST%\arrow.cur,%DEST%\help.cur,%DEST%\busybutclickable.ani,%DEST%\wait.ani,%DEST%\cross.cur,%DEST%\ibeam.cur,,%DEST%\notallowed.cur,%DEST%\resizenorthsouth.cur,%DEST%\resizeeastwest.cur,%DEST%\resizenorthwestsoutheast.cur,%DEST%\resizenortheastsouthwest.cur,%DEST%\move.cur,,%DEST%\pointinghand.cur,,"
reg add "HKCU\Control Panel\Cursors\Schemes" /v "%SCHEME%" /t REG_SZ /d "%LIST%" /f >nul
reg add "HKCU\Control Panel\Cursors" /ve /t REG_SZ /d "%SCHEME%" /f >nul
reg add "HKCU\Control Panel\Cursors" /v Arrow /t REG_SZ /d "%DEST%\arrow.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v Help /t REG_SZ /d "%DEST%\help.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v AppStarting /t REG_SZ /d "%DEST%\busybutclickable.ani" /f >nul
reg add "HKCU\Control Panel\Cursors" /v Wait /t REG_SZ /d "%DEST%\wait.ani" /f >nul
reg add "HKCU\Control Panel\Cursors" /v Crosshair /t REG_SZ /d "%DEST%\cross.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v IBeam /t REG_SZ /d "%DEST%\ibeam.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v NWPen /t REG_SZ /d "" /f >nul
reg add "HKCU\Control Panel\Cursors" /v No /t REG_SZ /d "%DEST%\notallowed.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v SizeNS /t REG_SZ /d "%DEST%\resizenorthsouth.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v SizeWE /t REG_SZ /d "%DEST%\resizeeastwest.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v SizeNWSE /t REG_SZ /d "%DEST%\resizenorthwestsoutheast.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v SizeNESW /t REG_SZ /d "%DEST%\resizenortheastsouthwest.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v SizeAll /t REG_SZ /d "%DEST%\move.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v UpArrow /t REG_SZ /d "" /f >nul
reg add "HKCU\Control Panel\Cursors" /v Hand /t REG_SZ /d "%DEST%\pointinghand.cur" /f >nul
reg add "HKCU\Control Panel\Cursors" /v Pin /t REG_SZ /d "" /f >nul
reg add "HKCU\Control Panel\Cursors" /v Person /t REG_SZ /d "" /f >nul

echo [3/3] Reloading the cursor set ...
rundll32.exe user32.dll,UpdatePerUserSystemParameters
powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -MemberDefinition '[DllImport(\"user32.dll\")] public static extern bool SystemParametersInfo(int u, int p, System.IntPtr v, int f);' -Name CursorApi -Namespace Win32; [void][Win32.CursorApi]::SystemParametersInfo(87, 0, [System.IntPtr]::Zero, 0)"

echo.
echo Done - the macOS 27 Golden Gate Large cursors are now active.
echo To undo: Mouse settings - Pointers - choose "Windows Default" and click Apply.
echo.
pause
endlocal
