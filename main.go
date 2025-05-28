package main

import (
	"adb-auto-player/internal"
	"adb-auto-player/internal/config"
	"adb-auto-player/internal/ipc"
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/logger"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/windows"
	"os"
	"path/filepath"
	stdruntime "runtime"
	"strings"
)

//go:embed all:frontend/build
var assets embed.FS

//go:embed wails.json
var wailsJSON []byte

type WailsInfo struct {
	ProductVersion string `json:"productVersion"`
}

type WailsConfig struct {
	Info WailsInfo `json:"info"`
}

func getWailsConfig() (*WailsConfig, error) {
	var wailsConfig WailsConfig
	if err := json.Unmarshal(wailsJSON, &wailsConfig); err != nil {
		return nil, err
	}
	return &wailsConfig, nil
}

func main() {
	println()
	wailsConfig, err := getWailsConfig()
	isDev := false

	if err != nil || wailsConfig == nil {
		println("Error retrieving config:", err)
		isDev = true
	} else {
		println("ProductVersion:", wailsConfig.Info.ProductVersion)
		isDev = wailsConfig.Info.ProductVersion == "0.0.0"
	}

	if !isDev {
		changeWorkingDirForProd()
	}

	logLevel := logger.INFO

	paths := []string{
		"config.toml",              // distributed
		"config/config.toml",       // dev
		"../../config/config.toml", // macOS dev no not a joke
	}

	configPath := internal.GetFirstPathThatExists(paths)
	mainConfig := config.NewMainConfig()
	if nil != configPath {
		loadedConfig, err := config.LoadMainConfig(*configPath)
		if err != nil {
			println(err.Error())
		} else {
			mainConfig = *loadedConfig
		}
	}
	println("MainConfig.Logging.Level:", mainConfig.Logging.Level)
	switch mainConfig.Logging.Level {
	case string(ipc.LogLevelTrace):
		logLevel = logger.TRACE
	case string(ipc.LogLevelDebug):
		logLevel = logger.DEBUG
	case string(ipc.LogLevelWarning):
		logLevel = logger.WARNING
	case string(ipc.LogLevelError):
		logLevel = logger.ERROR
	default:
		logLevel = logger.INFO
	}

	println("LogLevel:", logLevel)
	frontendLogger := ipc.NewFrontendLogger(uint8(logLevel))
	internal.GetProcessManager().ActionLogLimit = mainConfig.Logging.ActionLogLimit

	app := NewApp()

	err = wails.Run(&options.App{
		Title:  "AdbAutoPlayer",
		Width:  1168,
		Height: 776,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		BackgroundColour: &options.RGBA{R: 0, G: 0, B: 0, A: 0},
		Windows: &windows.Options{
			WindowIsTranslucent:  false,
			WebviewIsTransparent: false,
			Theme:                windows.Dark,
			BackdropType:         windows.Mica,
			WebviewGpuIsDisabled: false,
		},
		OnStartup: func(ctx context.Context) {
			app.Startup(ctx)
		},
		OnDomReady: func(ctx context.Context) {
			frontendLogger.Startup(ctx)
			internal.GetProcessManager().Logger = frontendLogger
		},
		OnShutdown: func(ctx context.Context) {
			app.Shutdown(ctx)
		},
		Bind: []interface{}{
			app,
		},
		Logger:             frontendLogger,
		LogLevel:           logLevel,
		LogLevelProduction: logLevel,
	})

	if err != nil {
		panic(err)
	}
}

func changeWorkingDirForProd() {
	execPath, err := os.Executable()
	if err != nil {
		panic(fmt.Sprintf("Unable to get executable path: %v", err))
	}

	execDir := filepath.Dir(execPath)
	if stdruntime.GOOS != "windows" && strings.Contains(execDir, "internal.app") {
		execDir = filepath.Dir(filepath.Dir(filepath.Dir(filepath.Dir(execPath)))) // Go outside the .app bundle
	}
	if err := os.Chdir(execDir); err != nil {
		panic(fmt.Sprintf("Failed to change working directory to %s: %v", execDir, err))
	}

	_, err = os.Getwd()
	if err != nil {
		panic(err)
	}
}
