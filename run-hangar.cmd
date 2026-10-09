@echo off
setlocal
set "REBGE_ROOT=%~dp0"
if "%REBGE_ASSETS%"=="" set "REBGE_ASSETS=%REBGE_ROOT%asset-packs\stage43-runtime"
if not exist "%REBGE_ASSETS%\scenes\sally-hangar\scene.json" (
  echo Asset pack is missing. Set REBGE_ASSETS to its directory.
  exit /b 1
)
if not exist "%REBGE_ROOT%bevy\target\debug\rebge.exe" (
  echo Preview executable is missing. Build bevy/Cargo.toml first.
  pause
  exit /b 1
)
"%REBGE_ROOT%bevy\target\debug\rebge.exe" --assets "%REBGE_ASSETS%" --scene scenes/sally-hangar/scene.json
if errorlevel 1 pause
