package games

import (
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
	isDev                  bool
	pythonBinaryPath       *string
	games                  []ipc.GameGUI
	lastOpenGameConfigPath *string
}

func NewGamesService(isDev bool) *GamesService {
	return &GamesService{
		isDev: isDev,
		games: []ipc.GameGUI{}, // initialize empty slice
		// other fields will be their zero values (nil for pointers)
	}
}

func (g *GamesService) GetGameGUI(disableLogging bool) (*ipc.GameGUI, error) {
	if err := g.resolvePythonBinaryPathIfNeeded(); err != nil {
		return nil, err
	}

	if err := g.setGamesIfNeeded(); err != nil {
		return nil, err
	}

	runningGame := ""
	args := []string{"GetRunningGame"}
	if disableLogging {
		args = append(args, "--log-level=DISABLE")
	}
	output, err := process.Get().Exec(*g.pythonBinaryPath, args...)

	if err != nil {
		logger.Get().Errorf("%v", err)
		return nil, err
	}

	lines := strings.Split(output, "\n")
	for _, line := range lines {
		if line == "" {
			continue
		}

		var logMessage ipc.LogMessage
		if err = json.Unmarshal([]byte(line), &logMessage); err != nil {
			logger.Get().Errorf("Failed to parse JSON log message: %v", err)
			continue
		}

		if strings.HasPrefix(logMessage.Message, "Running game: ") {
			runningGame = strings.TrimSpace(strings.TrimPrefix(logMessage.Message, "Running game: "))
			break
		}
		logger.Get().LogMessage(logMessage)
	}

	if runningGame == "" {
		return nil, nil
	}

	for _, game := range g.games {
		if runningGame == game.GameTitle {
			return &game, nil
		}
	}
	if g.pythonBinaryPath == nil {
		logger.Get().Debugf("Python Binary Path: nil")
	} else {
		logger.Get().Debugf("Python Binary Path: %s", *g.pythonBinaryPath)
	}
	logger.Get().Debugf("App: %s not supported", runningGame)
	return nil, nil
}

func (g *GamesService) Debug() error {
	if err := g.resolvePythonBinaryPathIfNeeded(); err != nil {
		return err
	}

	args := []string{"Debug"}

	if err := process.Get().StartProcess(g.pythonBinaryPath, args, false, 2); err != nil {
		logger.Get().Errorf("Starting process: %v", err)

		return err
	}
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
	if err := process.Get().StartProcess(g.pythonBinaryPath, args, true); err != nil {
		logger.Get().Errorf("Starting process: %v", err)
		return err
	}
	return nil
}

func (g *GamesService) KillGameProcess() {
	process.Get().KillProcess()
}

func (g *GamesService) IsGameProcessRunning() bool {
	return process.Get().IsProcessRunning()
}

func (g *GamesService) resolvePythonBinaryPathIfNeeded() error {
	if g.pythonBinaryPath == nil {
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

	if process.Get().IsDev {
		pythonPath := filepath.Join(workingDir, "python")
		g.pythonBinaryPath = &pythonPath
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
	g.pythonBinaryPath = path.GetFirstPathThatExists(paths)
	return nil
}

func (g *GamesService) setGamesFromPython() error {
	if g.pythonBinaryPath == nil {
		return errors.New("missing files: https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/troubleshoot.html#missing-files")
	}

	gamesString, err := process.Get().Exec(*g.pythonBinaryPath, "GUIGamesMenu", "--log-level=DISABLE")
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

	if configPath == nil {
		g.lastOpenGameConfigPath = &paths[0]
		response := map[string]interface{}{
			"settings":    map[string]interface{}{},
			"constraints": game.Constraints,
		}

		return response, nil
	}

	g.lastOpenGameConfigPath = configPath

	gameConfig, err = settings.LoadTOML[map[string]interface{}](*configPath)
	if err != nil {

		return nil, err
	}

	response := map[string]interface{}{
		"settings":    gameConfig,
		"constraints": game.Constraints,
	}
	return response, nil
}

func (g *GamesService) SaveGameSettings(gameSettings map[string]interface{}) error {
	if nil == g.lastOpenGameConfigPath {
		return errors.New("cannot save game settings: no game settings found")
	}

	if err := settings.SaveTOML[map[string]interface{}](*g.lastOpenGameConfigPath, &gameSettings); err != nil {
		return err
	}
	logger.Get().Infof("Saving Game Settings")
	return g.setGamesFromPython()
}
