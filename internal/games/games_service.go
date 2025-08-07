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
	"log"
	"os"
	"path/filepath"
	stdruntime "runtime"
	"sync"
)

type GamesService struct {
	mu                     sync.Mutex
	gameGUI                *ipc.GameGUI
	lastOpenGameConfigPath string
}

func (g *GamesService) GetGameGUI() (*ipc.GameGUI, error) {
	if err := g.resolvePythonBinaryPathIfNeeded(); err != nil {
		return nil, err
	}

	logMessages, err := process.GetService().POSTCommand([]string{"DisplayGUI"})
	if err != nil {
		return nil, err
	}

	var gameGUI ipc.GameGUI

	if len(logMessages) == 0 {
		return nil, errors.New("empty Response from Python")
	}

	last := logMessages[len(logMessages)-1]
	if last.Level == "ERROR" {
		return nil, errors.New(last.Message)
	}

	err = json.Unmarshal([]byte(last.Message), &gameGUI)
	if err != nil {
		println(last.Message)
		println(err.Error())
		return nil, err
	}

	g.mu.Lock()
	g.gameGUI = &gameGUI
	result := g.gameGUI
	g.mu.Unlock()

	return result, nil
}

func (g *GamesService) Debug() error {
	if err := g.resolvePythonBinaryPathIfNeeded(); err != nil {
		return err
	}
	if err := process.GetService().StartTask([]string{"Debug"}, false, 2); err != nil {
		logger.Get().Errorf("Failed starting process: %v", err)
		return err
	}
	return nil
}

func (g *GamesService) SaveDebugZip() {
	const debugDir = "debug"

	var zipPath string
	if stdruntime.GOOS == "darwin" {
		cwd, err := os.Getwd()
		if err != nil {
			log.Fatalf("failed to get current directory: %v", err)
		}

		parentDir := filepath.Clean(filepath.Join(cwd, "..", "..", ".."))
		zipPath = filepath.Join(parentDir, "debug.zip")
	} else {
		zipPath = "debug.zip"

	}

	if _, err := os.Stat(debugDir); os.IsNotExist(err) {
		logger.Get().Errorf("debug directory does not exist")
		return
	}

	zipFile, err := os.Create(zipPath)
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
		executable = "adb_auto_player"
	}

	if stdruntime.GOOS == "darwin" {
		process.GetService().SetPythonBinaryPath(filepath.Join(workingDir, "../Resources/binaries", executable))
	} else {
		process.GetService().SetPythonBinaryPath(filepath.Join(workingDir, "binaries", executable))
	}
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
		filepath.Join(workingDir, "games", game.ConfigPath),                        // Windows .exe
		filepath.Join(workingDir, "python/adb_auto_player/games", game.ConfigPath), // Dev
		filepath.Join(workingDir, "../Resources/games", game.ConfigPath),           // MacOS .app Bundle
	}
	configPath := path.GetFirstPathThatExists(paths)

	g.mu.Lock()
	if configPath == "" {
		if stdruntime.GOOS == "darwin" {
			g.lastOpenGameConfigPath = filepath.Join(workingDir, "../Resources/games", game.ConfigPath)
		} else {
			g.lastOpenGameConfigPath = filepath.Join(workingDir, "games", game.ConfigPath)
		}
		g.mu.Unlock()
		response := map[string]interface{}{
			"settings":    map[string]interface{}{},
			"constraints": game.Constraints,
		}

		return response, nil
	}

	g.lastOpenGameConfigPath = configPath
	g.mu.Unlock()

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
	g.mu.Lock()
	defer app.Emit(event_names.GameSettingsUpdated)
	defer g.mu.Unlock()

	if g.lastOpenGameConfigPath == "" || nil == g.gameGUI {
		return nil, errors.New("cannot save game settings: no game settings found")
	}

	if err := settings.SaveTOML[map[string]interface{}](g.lastOpenGameConfigPath, &gameSettings); err != nil {
		return nil, err
	}
	logger.Get().Infof("Saving Game Settings")

	g.lastOpenGameConfigPath = ""

	displayNames := make(map[string]string)
	for key, value := range gameSettings {
		if nestedMap, ok := value.(map[string]interface{}); ok {
			if displayName, okDN := nestedMap["Display Name"].(string); okDN {
				displayNames[key] = displayName
			}
		}
	}

	for i, option := range g.gameGUI.MenuOptions {
		if displayName, exists := displayNames[option.Label]; exists {
			g.gameGUI.MenuOptions[i].CustomLabel = displayName
		}
	}

	return g.gameGUI, nil
}
