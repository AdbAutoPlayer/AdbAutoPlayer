package main

import (
	"adb-auto-player/internal/config"
	"adb-auto-player/internal/ipc"
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
	"path/filepath"
	stdruntime "runtime"
	"strings"
)

type App struct {
	ctx                    context.Context
	pythonBinaryPath       *string
	killAdbOnShutdown      bool
	games                  []ipc.GameGUI
	lastOpenGameConfigPath *string
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
		return errors.New("no python executable found")
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

func (a *App) GetEditableMainConfig() (map[string]interface{}, error) {
	paths := []string{
		"config.toml",
	}
	if stdruntime.GOOS == "darwin" {
		paths = append(paths, "../../config.toml")
	}
	configPath := GetFirstPathThatExists(paths)

	mainConfig, err := config.LoadConfig[config.MainConfig](*configPath)
	if err != nil {
		return nil, err
	}

	response := map[string]interface{}{
		"config":      mainConfig,
		"constraints": ipc.GetMainConfigConstraints(),
	}
	return response, nil
}

func (a *App) SaveMainConfig(mainConfig config.MainConfig) error {
	if err := config.SaveConfig[config.MainConfig]("config.toml", &mainConfig); err != nil {
		return err
	}
	runtime.LogInfo(a.ctx, "Saved Main config")
	GetProcessManager().logger.SetLogLevelFromString(mainConfig.Logging.Level)
	runtime.LogSetLogLevel(a.ctx, logger.LogLevel(ipc.GetLogLevelFromString(mainConfig.Logging.Level)))
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
		errorText := fmt.Sprintf(
			"no %s config found at %s",
			game.GameTitle,
			strings.Join(paths, ", "),
		)
		runtime.LogErrorf(a.ctx, "%s", errorText)
		return nil, errors.New(errorText)
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

func (a *App) GetRunningSupportedGame() (*ipc.GameGUI, error) {
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

	for _, game := range a.games {
		// TODO we only have a single game right now anyway
		// Original idea was to detect what game is running
		// We can add a command on python for this
		// Or remove this and have a select in the GUI
		return &game, nil
	}
	if a.pythonBinaryPath == nil {
		runtime.LogDebugf(a.ctx, "Python Binary Path: nil")
	} else {
		runtime.LogDebugf(a.ctx, "Python Binary Path: %s", *a.pythonBinaryPath)
	}
	return nil, fmt.Errorf("should never happen")
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
	pm := GetProcessManager()
	pm.blocked = true
	defer func() { pm.blocked = false }()
	runtime.LogInfo(a.ctx, "Downloading update")
	response, err := http.Get(assetUrl)
	if err != nil {
		return fmt.Errorf("failed to download file: %v", err)
	}
	defer response.Body.Close()

	tempFile, err := os.CreateTemp("", "patch-*.zip")
	if err != nil {
		return fmt.Errorf("failed to create temp file: %v", err)
	}
	defer tempFile.Close()

	_, err = io.Copy(tempFile, response.Body)
	if err != nil {
		return fmt.Errorf("failed to save downloaded file: %v", err)
	}

	zipReader, err := zip.OpenReader(tempFile.Name())
	if err != nil {
		return fmt.Errorf("failed to open zip file: %v", err)
	}
	defer zipReader.Close()

	if err = os.MkdirAll(".", 0755); err != nil {
		return fmt.Errorf("failed to create target directory: %v", err)
	}

	for _, file := range zipReader.File {
		outputPath := filepath.Join(".", file.Name)

		if file.FileInfo().IsDir() {
			if err = os.MkdirAll(outputPath, file.Mode()); err != nil {
				return fmt.Errorf("failed to create directory: %v", err)
			}
			continue
		}

		if err = os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
			return fmt.Errorf("failed to create directories: %v", err)
		}

		fileInZip, err := file.Open()
		if err != nil {
			return fmt.Errorf("failed to open file in zip archive: %v", err)
		}
		defer fileInZip.Close()

		outputFile, err := os.Create(outputPath)
		if err != nil {
			return fmt.Errorf("failed to create extracted file: %v", err)
		}
		defer outputFile.Close()

		_, err = io.Copy(outputFile, fileInZip)
		if err != nil {
			return fmt.Errorf("failed to copy file data: %v", err)
		}
	}

	runtime.LogInfo(a.ctx, "Update successful")
	return nil
}
