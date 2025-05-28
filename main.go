package main

import (
	"adb-auto-player/internal"
	"adb-auto-player/internal/config"
	"adb-auto-player/internal/ipc"
	"context"
	"embed"
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

// Version is set at build time using -ldflags "-X main.Version=..."
var Version = "dev" // default fallback for local dev runs

func main() {
	println()
	println("Version:", Version)
	isDev := Version == "dev"

	if !isDev {
		changeWorkingDirForProd()
		// TODO updater
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

	app := NewApp(Version)

	appErr := wails.Run(&options.App{
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

	if appErr != nil {
		panic(appErr)
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
