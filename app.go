package main

import (
	"adb-auto-player/internal"
	"adb-auto-player/internal/config"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/updater"
	"archive/zip"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/wailsapp/wails/v2/pkg/logger"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	stdruntime "runtime"
	"strings"
	"time"
)

type App struct {
	ctx                    context.Context
	pythonBinaryPath       *string
	games                  []ipc.GameGUI
	lastOpenGameConfigPath *string
	mainConfigPath         *string
	version                string
	isDev                  bool
	mainConfig             config.MainConfig
}

func NewApp(version string, isDev bool, mainConfig config.MainConfig) *App {
	newApp := &App{
		version:          version,
		pythonBinaryPath: nil,
		games:            []ipc.GameGUI{},
	}
	return newApp
}

func (a *App) CheckForUpdates() updater.UpdateInfo {
	if a.isDev {
		return updater.UpdateInfo{Available: false}
	}
	resp, err := http.Get("https://api.github.com/repos/AdbAutoPlayer/AdbAutoPlayer/releases/latest")
	if err != nil {
		return updater.UpdateInfo{Error: err.Error()}
	}
	defer func() {
		if err = resp.Body.Close(); err != nil {
			runtime.LogErrorf(a.ctx, "resp.Body.Close error: %v", err)
		}
	}()

	var release updater.GitHubRelease
	if err := json.NewDecoder(resp.Body).Decode(&release); err != nil {
		return updater.UpdateInfo{Error: err.Error()}
	}

	if release.TagName != a.version {
		// Find the Windows asset
		var windowsAsset *struct {
			BrowserDownloadURL string `json:"browser_download_url"`
			Size               int64  `json:"size"`
			Name               string `json:"name"`
		}

		for _, asset := range release.Assets {
			if strings.Contains(strings.ToLower(asset.Name), "windows") ||
				strings.Contains(strings.ToLower(asset.Name), "win") {
				windowsAsset = &asset
				break
			}
		}

		if windowsAsset == nil && len(release.Assets) > 0 {
			// Fallback to first asset if no Windows-specific asset found
			windowsAsset = &release.Assets[0]
		}

		if windowsAsset != nil {
			return updater.UpdateInfo{
				Available:   true,
				Version:     release.TagName,
				DownloadURL: windowsAsset.BrowserDownloadURL,
				Size:        windowsAsset.Size,
			}
		}
	}

	return updater.UpdateInfo{Available: false}
}

func (a *App) DownloadUpdate(downloadURL string) error {
	resp, err := http.Get(downloadURL)
	if err != nil {
		return err
	}
	defer func() {
		if err = resp.Body.Close(); err != nil {
			runtime.LogErrorf(a.ctx, "resp.Body.Close error: %v", err)
		}
	}()

	// Create temp directory
	tempDir := filepath.Join(os.TempDir(), "adbautoplayer-update")
	if err = os.RemoveAll(tempDir); err != nil {
		return err
	}
	if err = os.MkdirAll(tempDir, 0755); err != nil {
		return err
	}

	tempFile := filepath.Join(tempDir, "update.zip")

	out, err := os.Create(tempFile)
	if err != nil {
		return err
	}
	defer func() {
		if err = out.Close(); err != nil {
			runtime.LogErrorf(a.ctx, "out.Close error: %v", err)
		}
	}()

	// Download with progress reporting
	totalSize := resp.ContentLength
	var downloaded int64

	buffer := make([]byte, 32*1024) // 32KB buffer
	for {
		n, err := resp.Body.Read(buffer)
		if n > 0 {
			if _, writeErr := out.Write(buffer[:n]); writeErr != nil {
				return writeErr
			}
			downloaded += int64(n)

			// Emit progress to frontend
			if totalSize > 0 {
				progress := float64(downloaded) / float64(totalSize) * 100
				runtime.EventsEmit(a.ctx, "download-progress", progress)
			}
		}

		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
	}

	// Extract and apply update
	return a.extractAndApplyUpdate(tempFile)
}

func (a *App) extractAndApplyUpdate(zipPath string) error {
	// Get current executable path
	exePath, err := os.Executable()
	if err != nil {
		return err
	}
	appDir := filepath.Dir(exePath)

	// Extract zip to temp location first
	tempExtractDir := filepath.Join(filepath.Dir(zipPath), "extracted")
	if err := os.MkdirAll(tempExtractDir, 0755); err != nil {
		return err
	}

	if err := updater.Unzip(a.ctx, zipPath, tempExtractDir); err != nil {
		return err
	}

	// Create update script (batch file for Windows)
	scriptPath := filepath.Join(filepath.Dir(zipPath), "update.bat")
	exeName := filepath.Base(exePath)

	// Script that waits, kills process, copies files, and restarts
	script := fmt.Sprintf(`@echo off
echo Preparing to update...
timeout /t 3 /nobreak >nul

echo Stopping application...
taskkill /f /im "%s" >nul 2>&1
timeout /t 2 /nobreak >nul

echo Updating files...
xcopy /s /y /q "%s\*" "%s\"
if errorlevel 1 (
    echo Update failed!
    pause
    exit /b 1
)

echo Starting application...
cd /d "%s"
start "" "%s"

echo Cleaning up...
timeout /t 2 /nobreak >nul
rd /s /q "%s" >nul 2>&1
del "%%~f0" >nul 2>&1
`, exeName, tempExtractDir, appDir, appDir, exePath, filepath.Dir(zipPath))

	if err := os.WriteFile(scriptPath, []byte(script), 0755); err != nil {
		return err
	}

	// Execute update script and exit current application
	cmd := exec.Command("cmd", "/c", scriptPath)
	if err := cmd.Start(); err != nil {
		return err
	}

	// Give the script a moment to start, then exit
	runtime.EventsEmit(a.ctx, "download-progress", 100)

	// Exit current app - the script will restart it
	go func() {
		// Small delay to ensure the script starts
		time.Sleep(1 * time.Second)
		os.Exit(0)
	}()

	return nil
}

func (a *App) setGamesFromPython() error {
	if a.pythonBinaryPath == nil {
		return errors.New("missing files: https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/troubleshoot.html#missing-files")
	}

	gamesString, err := internal.GetProcessManager().Exec(*a.pythonBinaryPath, "GUIGamesMenu", "--log-level=DISABLE")
	if err != nil {
		return err
	}
	var gameGUIs []ipc.GameGUI

	err = json.Unmarshal([]byte(gamesString), &gameGUIs)
	if err != nil {
		return err
	}

	a.games = gameGUIs

	return nil
}

func (a *App) Startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) Shutdown(ctx context.Context) {
	a.ctx = ctx
	_, err := internal.GetProcessManager().KillProcess()
	if err != nil {
		panic(err)
	}
}

func (a *App) GetEditableMainConfig() map[string]interface{} {
	mainConfig, err := config.LoadMainConfig(a.getMainConfigPath())
	if err != nil {
		runtime.LogDebugf(a.ctx, "%v", err)
		tmp := config.NewMainConfig()
		mainConfig = &tmp
	}

	response := map[string]interface{}{
		"config":      mainConfig,
		"constraints": ipc.GetMainConfigConstraints(),
	}
	return response
}

func (a *App) SaveMainConfig(mainConfig config.MainConfig) error {
	if err := config.SaveConfig[config.MainConfig](a.getMainConfigPath(), &mainConfig); err != nil {
		return err
	}
	a.mainConfig = mainConfig
	runtime.EventsEmit(a.ctx, "log-clear")
	internal.GetProcessManager().Logger.SetLogLevelFromString(mainConfig.Logging.Level)
	runtime.LogSetLogLevel(a.ctx, logger.LogLevel(ipc.GetLogLevelFromString(mainConfig.Logging.Level)))
	runtime.LogInfo(a.ctx, "Saved Main config")
	return nil
}

func (a *App) GetEditableGameConfig(game ipc.GameGUI) (map[string]interface{}, error) {
	var gameConfig interface{}
	var err error

	workingDir, err := os.Getwd()
	if err != nil {
		runtime.LogErrorf(a.ctx, "Failed to get current working directory: %v", err)
		return nil, err
	}

	paths := []string{
		filepath.Join(workingDir, "games", game.ConfigPath),
		filepath.Join(workingDir, "python/adb_auto_player/games", game.ConfigPath),
	}
	if stdruntime.GOOS != "windows" {
		paths = append(paths, filepath.Join(workingDir, "../../python/adb_auto_player/games", game.ConfigPath))
	}
	configPath := internal.GetFirstPathThatExists(paths)

	if configPath == nil {
		a.lastOpenGameConfigPath = &paths[0]
		response := map[string]interface{}{
			"config":      map[string]interface{}{},
			"constraints": game.Constraints,
		}

		return response, nil
	}

	a.lastOpenGameConfigPath = configPath

	gameConfig, err = config.LoadConfig[map[string]interface{}](*configPath)
	if err != nil {

		return nil, err
	}

	response := map[string]interface{}{
		"config":      gameConfig,
		"constraints": game.Constraints,
	}
	return response, nil
}

func (a *App) GetTheme() string {
	mainConfig := config.NewMainConfig()
	loadedConfig, err := config.LoadMainConfig(a.getMainConfigPath())
	if err != nil {
		println(err.Error())
	} else {
		mainConfig = *loadedConfig
	}
	return mainConfig.UI.Theme
}

func (a *App) SaveGameConfig(gameConfig map[string]interface{}) error {
	if nil == a.lastOpenGameConfigPath {
		return errors.New("cannot save game config: no game config found")
	}

	if err := config.SaveConfig[map[string]interface{}](*a.lastOpenGameConfigPath, &gameConfig); err != nil {
		return err
	}
	runtime.LogInfo(a.ctx, "Saved config")
	return nil
}

func (a *App) GetRunningSupportedGame(disableLogging bool) (*ipc.GameGUI, error) {
	if a.pythonBinaryPath == nil {
		err := a.setPythonBinaryPath()
		if err != nil {
			runtime.LogErrorf(a.ctx, "%v", err)
			return nil, err
		}
	}
	if len(a.games) == 0 {
		err := a.setGamesFromPython()
		if err != nil {
			runtime.LogErrorf(a.ctx, "%v", err)
			return nil, err
		}
	}

	runningGame := ""
	args := []string{"GetRunningGame"}
	if disableLogging {
		args = append(args, "--log-level=DISABLE")
	}
	output, err := internal.GetProcessManager().Exec(*a.pythonBinaryPath, args...)

	if err != nil {
		runtime.LogErrorf(a.ctx, "%v", err)
		return nil, err
	}

	lines := strings.Split(output, "\n")
	for _, line := range lines {
		if line == "" {
			continue
		}

		var logMessage ipc.LogMessage
		if err := json.Unmarshal([]byte(line), &logMessage); err != nil {
			runtime.LogErrorf(a.ctx, "Failed to parse JSON log message: %v", err)
			continue
		}

		if strings.HasPrefix(logMessage.Message, "Running game: ") {
			runningGame = strings.TrimSpace(strings.TrimPrefix(logMessage.Message, "Running game: "))
			break
		}
		internal.GetProcessManager().Logger.LogMessage(logMessage)
	}

	if runningGame == "" {
		return nil, nil
	}

	for _, game := range a.games {
		if runningGame == game.GameTitle {
			return &game, nil
		}
	}
	if a.pythonBinaryPath == nil {
		runtime.LogDebugf(a.ctx, "Python Binary Path: nil")
	} else {
		runtime.LogDebugf(a.ctx, "Python Binary Path: %s", *a.pythonBinaryPath)
	}
	runtime.LogDebugf(a.ctx, "Package: %s not supported", runningGame)
	return nil, nil
}

func (a *App) setPythonBinaryPath() error {
	workingDir, err := os.Getwd()
	if err != nil {
		runtime.LogErrorf(a.ctx, "%v", err)
		return err
	}

	if runtime.Environment(a.ctx).BuildType == "dev" {
		fmt.Printf("Working dir: %s", workingDir)
		path := filepath.Join(workingDir, "python")
		if stdruntime.GOOS != "windows" {
			path = filepath.Join(workingDir, "../../python")
		}
		a.pythonBinaryPath = &path
		fmt.Print("Process Manager is dev = true\n")
		internal.GetProcessManager().IsDev = true
		return nil
	}

	executable := "adb_auto_player.exe"
	if stdruntime.GOOS != "windows" {
		executable = "adb_auto_player_py_app"
	}

	paths := []string{
		filepath.Join(workingDir, "binaries", executable),
	}

	if stdruntime.GOOS != "windows" {
		paths = append(paths, filepath.Join(workingDir, "../../../python/main.dist/", executable))
		paths = append(paths, filepath.Join(workingDir, "../../python/main.dist/", executable))

	} else {
		paths = append(paths, filepath.Join(workingDir, "python/main.dist/", executable))
	}

	runtime.LogDebugf(a.ctx, "Paths: %s", strings.Join(paths, ", "))
	a.pythonBinaryPath = internal.GetFirstPathThatExists(paths)
	return nil
}

func (a *App) Debug() error {
	args := []string{"Debug"}

	if err := internal.GetProcessManager().StartProcess(*a.pythonBinaryPath, args, 2); err != nil {
		runtime.LogErrorf(a.ctx, "Starting process: %v", err)

		return err
	}
	return nil
}

func (a *App) SaveDebugZip() {
	const debugDir = "debug"
	const zipName = "debug.zip"

	if _, err := os.Stat(debugDir); os.IsNotExist(err) {
		runtime.LogErrorf(a.ctx, "debug directory does not exist")
		return
	}

	zipFile, err := os.Create(zipName)
	if err != nil {
		runtime.LogErrorf(
			a.ctx,
			"%s",
			fmt.Errorf("failed to create zip file: %w", err),
		)
		return
	}
	defer func(zipFile *os.File) {
		err = zipFile.Close()
		if err != nil {
			runtime.LogErrorf(
				a.ctx,
				"%s",
				fmt.Errorf("%w", err),
			)
		}
	}(zipFile)

	zipWriter := zip.NewWriter(zipFile)
	defer func(zipWriter *zip.Writer) {
		err = zipWriter.Close()
		if err != nil {
			runtime.LogErrorf(
				a.ctx,
				"%s",
				fmt.Errorf("%w", err),
			)
		}
	}(zipWriter)

	err = filepath.Walk(debugDir, func(filePath string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			return nil
		}

		relPath, err := filepath.Rel(debugDir, filePath)
		if err != nil {
			return err
		}

		zipEntry, err := zipWriter.Create(relPath)
		if err != nil {
			return err
		}

		file, err := os.Open(filePath)
		if err != nil {
			return err
		}
		defer func(file *os.File) {
			err = file.Close()
			if err != nil {
				runtime.LogErrorf(
					a.ctx,
					"%s",
					fmt.Errorf("%w", err),
				)
			}
		}(file)

		_, err = io.Copy(zipEntry, file)
		return err
	})

	if err != nil {
		runtime.LogErrorf(
			a.ctx,
			"%s",
			fmt.Errorf("failed to create zip archive: %w", err),
		)
		return
	}

	runtime.LogInfof(a.ctx, "debug.zip saved")
}

func (a *App) StartGameProcess(args []string) error {
	if err := internal.GetProcessManager().StartProcess(*a.pythonBinaryPath, args); err != nil {
		runtime.LogErrorf(a.ctx, "Starting process: %v", err)
		return err
	}
	return nil
}

func (a *App) TerminateGameProcess() error {
	terminated, err := internal.GetProcessManager().KillProcess()
	if err != nil {
		runtime.LogErrorf(a.ctx, "Terminating process: %v", err)
		return err
	}
	if terminated {
		runtime.LogWarning(a.ctx, "Stopping")
	}
	return nil
}

func (a *App) IsGameProcessRunning() bool {
	return internal.GetProcessManager().IsProcessRunning()
}

func (a *App) GetAppVersion() string {
	return a.version
}

func (a *App) getMainConfigPath() string {
	if a.mainConfigPath != nil {
		return *a.mainConfigPath
	}

	paths := []string{
		"config.toml",              // distributed
		"config/config.toml",       // dev
		"../../config/config.toml", // macOS dev no not a joke
	}

	configPath := internal.GetFirstPathThatExists(paths)

	a.mainConfigPath = configPath

	if a.mainConfigPath == nil {
		return paths[0]
	}
	return *configPath
}
