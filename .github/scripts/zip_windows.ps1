$ErrorActionPreference = "Stop"

# Use GITHUB_WORKSPACE if set, otherwise default to two directories up from script location
$Workspace = $env:GITHUB_WORKSPACE
if (-not $Workspace) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $Workspace = Split-Path -Parent (Split-Path -Parent $ScriptDir)
}

$ReleaseZipDir = Join-Path $Workspace "AdbAutoPlayer"

if (-not (Test-Path $ReleaseZipDir)) {
    Write-Error "Release directory $ReleaseZipDir does not exist. Please run .github\scripts\build_windows.ps1 first."
    exit 1
}

$ZipFile = Join-Path $Workspace "AdbAutoPlayer_Windows.zip"
Compress-Archive -Path "$ReleaseZipDir\*" -DestinationPath $ZipFile -Force
Write-Output "ZIP file created at ${ZipFile}"

Write-Output "Files collected in ${ReleaseZipDir}:"
Get-ChildItem -Path $ReleaseZipDir -Recurse
