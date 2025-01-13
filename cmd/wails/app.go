package main

import (
	"adb-auto-player/games"
	"adb-auto-player/games/afkjourney"
	"adb-auto-player/internal/adb"
	"adb-auto-player/internal/config"
	"adb-auto-player/internal/ipc"
	"archive/zip"
	"context"
	"fmt"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"io"
	"net/http"
	"os"
	"path/filepath"
)

type App struct {
	ctx         context.Context
	useProdPath bool
}

func NewApp(useProdPath bool) *App {
	return &App{useProdPath: useProdPath}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) shutdown(ctx context.Context) {
	pm := GetProcessManager()
	_, err := pm.TerminateProcess()
	if err != nil {
		panic(err)
	}
}

func (a *App) GetEditableMainConfig() (map[string]interface{}, error) {
	mainConfig, err := config.LoadConfig[config.MainConfig]("config.toml")
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
	err := config.SaveConfig[config.MainConfig]("config.toml", &mainConfig)
	if err == nil {
		runtime.LogInfo(a.ctx, "Saved Main config")
		return nil
	}
	return err
}

func (a *App) GetEditableGameConfig(game games.Game) (map[string]interface{}, error) {
	var gameConfig interface{}
	var err error
	switch game.GameTitle {
	case "AFK Journey":
		gameConfig, err = config.LoadConfig[afkjourney.Config](game.ConfigPath)
	default:
		gameConfig, err = config.LoadConfig[map[string]interface{}](game.ConfigPath)
	}

	if err != nil {
		return nil, err
	}

	response := map[string]interface{}{
		"config":      gameConfig,
		"constraints": game.ConfigConstraints,
	}
	return response, nil
}

func (a *App) SaveAFKJourneyConfig(afkJourney games.Game, gameConfig afkjourney.Config) error {
	err := config.SaveConfig[afkjourney.Config](afkJourney.ConfigPath, &gameConfig)
	if err == nil {
		runtime.LogInfo(a.ctx, "Saved AFK Journey config")
		return nil
	}
	return err
}

func getAllGames(useProdPath bool) []games.Game {
	return []games.Game{
		afkjourney.NewAFKJourney(useProdPath),
	}
}

func (a *App) GetRunningSupportedGame() (*games.Game, error) {
	packageName, err := adb.GetRunningAppPackageName()
	if err != nil {
		runtime.LogErrorf(a.ctx, "%v", err)
		return nil, err
	}

	for _, game := range getAllGames(a.useProdPath) {
		for _, pName := range game.PackageNames {
			if pName == *packageName {
				return &game, nil
			}
		}
	}
	return nil, fmt.Errorf("%s is not supported", *packageName)
}

func (a *App) StartGameProcess(game games.Game, args []string) error {
	pm := GetProcessManager()
	err := pm.StartProcess(game.ExePath, args)
	if err != nil {
		runtime.LogErrorf(a.ctx, "Starting process: %v", err)
		return err
	}
	return nil
}

func (a *App) TerminateGameProcess() error {
	pm := GetProcessManager()
	terminated, err := pm.TerminateProcess()
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

	targetDir := "."
	err = os.MkdirAll(targetDir, 0755)
	if err != nil {
		return fmt.Errorf("failed to create target directory: %v", err)
	}

	for _, file := range zipReader.File {
		outputPath := filepath.Join(targetDir, file.Name)

		if file.FileInfo().IsDir() {
			err := os.MkdirAll(outputPath, file.Mode())
			if err != nil {
				return fmt.Errorf("failed to create directory: %v", err)
			}
			continue
		}

		err := os.MkdirAll(filepath.Dir(outputPath), 0755)
		if err != nil {
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
