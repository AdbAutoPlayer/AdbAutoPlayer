$Workspace = $env:GITHUB_WORKSPACE
$ReleaseZipDir = Join-Path $Workspace "release_zip"

New-Item -ItemType Directory -Force -Path $ReleaseZipDir

Copy-Item -Path "cmd/wails/build/bin/AdbAutoPlayer.exe" -Destination $ReleaseZipDir -Force
Copy-Item -Path "cmd/wails/config.toml" -Destination $ReleaseZipDir -Force
Copy-Item -Path "python/adb_auto_player.exe" -Destination $ReleaseZipDir -Force

$TemplatesDir = Join-Path $ReleaseZipDir "games/afk_journey/templates"
New-Item -ItemType Directory -Force -Path $TemplatesDir
Copy-Item -Path "python/adb_auto_player/games/afk_journey/templates/*" -Destination $TemplatesDir -Recurse -Force
Copy-Item -Path "python/adb_auto_player/games/afk_journey/AFKJourney.toml" -Destination (Join-Path $ReleaseZipDir "games/afk_journey") -Force

Write-Output "Files collected in ${ReleaseZipDir}:"
Get-ChildItem -Path $ReleaseZipDir -Recurse

$ZipFile = Join-Path $Workspace "AdbAutoPlayer_Windows.zip"
Compress-Archive -Path $ReleaseZipDir\* -DestinationPath $ZipFile -Force

Write-Output "ZIP file created at ${ZipFile}"
