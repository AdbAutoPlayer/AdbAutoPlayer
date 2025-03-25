package main

import (
	"adb-auto-player/internal/config"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/updater"
	"context"
	"encoding/json"
	"errors"
	"github.com/wailsapp/wails/v2/pkg/logger"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"os"
	"path/filepath"
	stdruntime "runtime"
	"strings"
	"time"
)

type App struct {
	ctx                    context.Context
	pythonBinaryPath       *string
	killAdbOnShutdown      bool
	games                  []ipc.GameGUI
	lastOpenGameConfigPath *string
	mainConfigPath         *string
}

func NewApp() *App {
	newApp := &App{
		pythonBinaryPath:  nil,
		killAdbOnShutdown: false,
		games:             []ipc.GameGUI{},
	}
	return newApp
}

func (a *App) setGamesFromPython() error {
	pm := GetProcessManager()

	if a.pythonBinaryPath == nil {
		return errors.New("missing files: https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/troubleshoot.html#missing-files")
	}

	gamesString, err := pm.Exec(*a.pythonBinaryPath, "GUIGamesMenu")
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

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	a.killAdbOnShutdown = !IsAdbRunning()
}

func (a *App) shutdown(ctx context.Context) {
	a.ctx = ctx
	pm := GetProcessManager()
	_, err := pm.KillProcess()
	if a.killAdbOnShutdown {
		KillAdbProcess()
	}
	if err != nil {
		panic(err)
	}
}

func (a *App) GetEditableMainConfig() map[string]interface{} {
	mainConfig, err := config.LoadConfig[config.MainConfig](a.getMainConfigPath())
	if err == nil {
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
	runtime.EventsEmit(a.ctx, "log-clear")
	GetProcessManager().logger.SetLogLevelFromString(mainConfig.Logging.Level)
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
		filepath.Join(workingDir, "../../python/adb_auto_player/games", game.ConfigPath),
	}
	if stdruntime.GOOS == "darwin" {
		paths = append(paths, filepath.Join(workingDir, "../../../../python/adb_auto_player/games", game.ConfigPath))
	}
	configPath := GetFirstPathThatExists(paths)

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

	pm := GetProcessManager()

	runningGame := ""
	args := []string{"GetRunningGame"}
	if disableLogging {
		args = append(args, "--log-level=DISABLE")
	}
	output, err := pm.Exec(*a.pythonBinaryPath, args...)

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
			pm.logger.Errorf("Failed to parse JSON log message: %v", err)
			continue
		}

		if strings.HasPrefix(logMessage.Message, "Running game: ") {
			runningGame = strings.TrimSpace(strings.TrimPrefix(logMessage.Message, "Running game: "))
			break
		}

		pm.logger.LogMessage(logMessage)
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

	executable := "adb_auto_player_py_app"
	if stdruntime.GOOS == "windows" {
		executable = "adb_auto_player.exe"
	}

	paths := []string{
		filepath.Join(workingDir, "binaries", executable),
	}

	if stdruntime.GOOS == "darwin" {
		paths = append(paths, filepath.Join(workingDir, "../../../../../python/main.dist/", executable))
	} else {
		paths = append(paths, filepath.Join(workingDir, "../../python/main.dist/", executable))
	}
	runtime.LogDebugf(a.ctx, "Paths: %s", strings.Join(paths, ", "))
	a.pythonBinaryPath = GetFirstPathThatExists(paths)
	return nil
}

func (a *App) StartGameProcess(args []string) error {
	pm := GetProcessManager()
	if err := pm.StartProcess(*a.pythonBinaryPath, args); err != nil {
		runtime.LogErrorf(a.ctx, "Starting process: %v", err)
		return err
	}
	return nil
}

func (a *App) TerminateGameProcess() error {
	pm := GetProcessManager()
	terminated, err := pm.KillProcess()
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
	pm := GetProcessManager()
	return pm.IsProcessRunning()
}

func (a *App) UpdatePatch(assetUrl string) error {
	runtime.LogInfo(a.ctx, "Downloading update")
	pm := GetProcessManager()
	pm.blocked = true
	defer func() { pm.blocked = false }()

	maxRetries := 3
	for i := 0; i < maxRetries; i++ {
		_, err := pm.KillProcess()
		if err == nil {
			break
		}
		if i < maxRetries-1 {
			time.Sleep(1 * time.Second)
		} else {
			runtime.LogDebugf(a.ctx, "Failed to kill process after retries: %v", err)
		}
	}
	time.Sleep(3 * time.Second)

	err := updater.UpdatePatch(assetUrl)
	if err != nil {
		runtime.LogErrorf(a.ctx, "Failed to update: %v", err)
		return err
	}

	runtime.LogInfo(a.ctx, "Update successful")
	return nil
}

func (a *App) getMainConfigPath() string {
	if a.mainConfigPath != nil {
		return *a.mainConfigPath
	}

	paths := []string{
		"config.toml",                    // distributed
		"../../config/config.toml",       // dev
		"../../../../config/config.toml", // macOS dev no not a joke
	}

	configPath := GetFirstPathThatExists(paths)

	a.mainConfigPath = configPath

	if a.mainConfigPath == nil {
		return paths[0]
	}
	return *configPath
}
