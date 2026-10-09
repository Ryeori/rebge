param(
    [string]$Assets = $(if ($env:REBGE_ASSETS) { $env:REBGE_ASSETS } else { Join-Path $PSScriptRoot '..\asset-packs\stage43-runtime' }),
    [string]$Scene,
    [string]$CaptureDirectory = (Join-Path $PSScriptRoot '..\reports\bevy\captures'),
    [ValidateSet('en','ru')][string]$Locale = 'ru',
    [switch]$Capture
)
$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot 'target\debug\rebge.exe'
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Build first: cargo build --locked' }
if (-not $Scene) {
    $Scene = if (Test-Path -LiteralPath (Join-Path $Assets 'scenes/sally-hangar/scene.json')) { 'scenes/sally-hangar/scene.json' } elseif (Test-Path -LiteralPath (Join-Path $Assets 'scene.json')) { 'scene.json' } else { 'scenes/D90057F0/scene.json' }
}
$arguments = @('--assets', $Assets, '--scene', $Scene)
$localization = Join-Path $Assets "texts\$Locale\4900FDC5.json"
if (Test-Path -LiteralPath $localization) {
    $arguments += @('--localization', $localization, '--text-key', 'InvC_Menu_NewGameStandard')
}
if ($Capture) {
    $env:RUST_LOG = 'info'
    New-Item -ItemType Directory -Path $CaptureDirectory -Force | Out-Null
    $capturePath = Join-Path $CaptureDirectory ('bevy-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.png')
    $arguments += @('--screenshot', $capturePath, '--exit-after-capture')
    & $runtime @arguments 2>&1 | Tee-Object -FilePath (Join-Path $PSScriptRoot '..\reports\bevy\bevy-run.log')
    if ($LASTEXITCODE -ne 0) { throw "Runtime failed: $LASTEXITCODE" }
    if (-not (Test-Path -LiteralPath $capturePath)) { throw 'Screenshot was not created' }
    Write-Output "Screenshot: $capturePath"
} else {
    & $runtime @arguments
}
