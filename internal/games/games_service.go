package games

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/path"
	"adb-auto-player/internal/process"
	"adb-auto-player/internal/settings"
	"archive/zip"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	stdruntime "runtime"
	"strings"
)

type GamesService struct {
	games                  []ipc.GameGUI
	runningGame            string
	lastOpenGameConfigPath string
}

func NewGamesService() *GamesService {
	return &GamesService{
		games: []ipc.GameGUI{}, // initialize empty slice
		// other fields will be their zero values (nil for pointers)
	}
}

func (g *GamesService) GetGameGUI() (*ipc.GameGUI, error) {
	if err := g.resolvePythonBinaryPathIfNeeded(); err != nil {
		return nil, err
	}

	if err := g.setGamesIfNeeded(); err != nil {
		return nil, err
	}

	runningGame, err := process.GetService().Exec([]string{"GetRunningGame", "--log-level=DISABLE"})
	if err != nil {
		logger.Get().Errorf("%v", err)
		return nil, err
	}
	g.runningGame = strings.TrimSpace(runningGame)
	if g.runningGame == "" {
		return nil, nil
	}

	return g.getActiveGameGUI()
}

func (g *GamesService) getActiveGameGUI() (*ipc.GameGUI, error) {
	for _, game := range g.games {
		if g.runningGame == game.GameTitle {
			return &game, nil
		}
	}

	logger.Get().Debugf("Game: %s not supported", g.runningGame)
	return nil, nil
}

func (g *GamesService) Debug() error {
	if err := g.resolvePythonBinaryPathIfNeeded(); err != nil {
		return err
	}
	originalLogLevel := logger.Get().LogLevel
	logger.Get().LogLevel = 2
	if err := process.GetService().StartTask([]string{"Debug"}, false); err != nil {
		logger.Get().Errorf("Failed starting process: %v", err)
		logger.Get().LogLevel = originalLogLevel
		return err
	}
	logger.Get().LogLevel = originalLogLevel
	return nil
}

func (g *GamesService) SaveDebugZip() {
	const debugDir = "debug"
	const zipName = "debug.zip"

	if _, err := os.Stat(debugDir); os.IsNotExist(err) {
		logger.Get().Errorf("debug directory does not exist")
		return
	}

	zipFile, err := os.Create(zipName)
	if err != nil {
		logger.Get().Errorf("%s", fmt.Errorf("failed to create zip file: %w", err))
		return
	}
	defer func(zipFile *os.File) {
		err = zipFile.Close()
		if err != nil {
			logger.Get().Errorf("%s", fmt.Errorf("%w", err))
		}
	}(zipFile)

	zipWriter := zip.NewWriter(zipFile)
	defer func(zipWriter *zip.Writer) {
		err = zipWriter.Close()
		if err != nil {
			logger.Get().Errorf("%s", fmt.Errorf("%w", err))
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
				logger.Get().Errorf("%s", fmt.Errorf("%w", err))
			}
		}(file)

		_, err = io.Copy(zipEntry, file)
		return err
	})

	if err != nil {
		logger.Get().Errorf("%s", fmt.Errorf("failed to create zip archive: %w", err))
		return
	}

	logger.Get().Infof("debug.zip saved")
}

func (g *GamesService) StartGameProcess(args []string) error {
	if err := process.GetService().StartTask(args, true); err != nil {
		logger.Get().Errorf("Failed starting process: %v", err)
		return err
	}
	return nil
}

func (g *GamesService) KillGameProcess() {
	process.GetService().StopTask()
}

func (g *GamesService) IsGameProcessRunning() bool {
	return process.GetService().IsTaskRunning()
}

func (g *GamesService) resolvePythonBinaryPathIfNeeded() error {
	if process.GetService().GetPythonBinaryPath() == "" {
		err := g.setPythonBinaryPath()
		if err != nil {
			logger.Get().Errorf("Error resolving python binary path: %v", err)
			return err
		}
	}

	return nil
}

func (g *GamesService) setGamesIfNeeded() error {
	if len(g.games) == 0 {
		err := g.setGamesFromPython()
		if err != nil {
			logger.Get().Errorf("%v", err)
			return err
		}
	}
	return nil
}

func (g *GamesService) setPythonBinaryPath() error {
	workingDir, err := os.Getwd()
	if err != nil {
		return err
	}

	if process.GetService().IsDev {
		pythonPath := filepath.Join(workingDir, "python")
		process.GetService().SetPythonBinaryPath(pythonPath)
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

	logger.Get().Debugf("Paths: %s", strings.Join(paths, ", "))
	process.GetService().SetPythonBinaryPath(path.GetFirstPathThatExists(paths))
	return nil
}

func (g *GamesService) setGamesFromPython() error {
	gamesString, err := process.GetService().Exec([]string{"GUIGamesMenu", "--log-level=DISABLE"})
	if err != nil {
		return err
	}
	var gameGUIs []ipc.GameGUI

	err = json.Unmarshal([]byte(gamesString), &gameGUIs)
	if err != nil {
		return err
	}

	g.games = gameGUIs

	return nil
}

func (g *GamesService) GetGameSettingsForm(game ipc.GameGUI) (map[string]interface{}, error) {
	var gameConfig interface{}
	var err error

	workingDir, err := os.Getwd()
	if err != nil {
		logger.Get().Errorf("Failed to get current working directory: %v", err)
		return nil, err
	}

	paths := []string{
		filepath.Join(workingDir, "games", game.ConfigPath),
		filepath.Join(workingDir, "python/adb_auto_player/games", game.ConfigPath),
	}
	if stdruntime.GOOS != "windows" {
		paths = append(paths, filepath.Join(workingDir, "../../python/adb_auto_player/games", game.ConfigPath))
	}
	configPath := path.GetFirstPathThatExists(paths)

	if configPath == "" {
		g.lastOpenGameConfigPath = paths[0]
		response := map[string]interface{}{
			"settings":    map[string]interface{}{},
			"constraints": game.Constraints,
		}

		return response, nil
	}

	g.lastOpenGameConfigPath = configPath

	gameConfig, err = settings.LoadTOML[map[string]interface{}](configPath)
	if err != nil {

		return nil, err
	}

	response := map[string]interface{}{
		"settings":    gameConfig,
		"constraints": game.Constraints,
	}
	return response, nil
}

func (g *GamesService) SaveGameSettings(gameSettings map[string]interface{}) (*ipc.GameGUI, error) {
	defer app.Emit(event_names.GameSettingsUpdated)

	if g.lastOpenGameConfigPath == "" {
		return nil, errors.New("cannot save game settings: no game settings found")
	}

	if err := settings.SaveTOML[map[string]interface{}](g.lastOpenGameConfigPath, &gameSettings); err != nil {
		return nil, err
	}
	logger.Get().Infof("Saving Game Settings")

	g.lastOpenGameConfigPath = ""
	gameGUI, err := g.getActiveGameGUI()
	if err != nil {
		return nil, err
	}

	displayNames := make(map[string]string)
	for key, value := range gameSettings {
		if nestedMap, ok := value.(map[string]interface{}); ok {
			if displayName, okDN := nestedMap["Display Name"].(string); okDN {
				displayNames[key] = displayName
			}
		}
	}

	for i, option := range gameGUI.MenuOptions {
		if displayName, exists := displayNames[option.Label]; exists {
			gameGUI.MenuOptions[i].CustomLabel = displayName
		}
	}

	for i, game := range g.games {
		if game.GameTitle == gameGUI.GameTitle {
			g.games[i] = *gameGUI
			break
		}
	}

	return gameGUI, nil
}
