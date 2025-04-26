package main

import (
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

func main() {
	changeWorkingDirForProd()

	logLevel := logger.INFO

	paths := []string{
		"config.toml",                    // distributed
		"../../config/config.toml",       // dev
		"../../../../config/config.toml", // macOS dev no not a joke
	}

	configPath := GetFirstPathThatExists(paths)
	mainConfig := config.NewMainConfig()
	if nil != configPath {
		loadedConfig, err := config.LoadMainConfig(*configPath)
		if err != nil {
			println(err.Error())
		} else {
			mainConfig = *loadedConfig
		}
	}
	println(mainConfig.Logging.Level)
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

	println(logLevel)
	frontendLogger := ipc.NewFrontendLogger(uint8(logLevel))
	GetProcessManager().actionLogLimit = mainConfig.Logging.ActionLogLimit

	app := NewApp()

	err := wails.Run(&options.App{
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
			app.startup(ctx)
		},
		OnDomReady: func(ctx context.Context) {
			frontendLogger.Startup(ctx)
			GetProcessManager().logger = frontendLogger
		},
		OnShutdown: func(ctx context.Context) {
			app.shutdown(ctx)
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
	for _, arg := range os.Args {
		if strings.Contains(arg, "wailsbindings") {
			_, err := os.Getwd()
			if err != nil {
				panic(err)
			}
			return
		}
	}

	execPath, err := os.Executable()
	if err != nil {
		panic(fmt.Sprintf("Unable to get executable path: %v", err))
	}

	if !strings.HasSuffix(execPath, "-dev.exe") {
		execDir := filepath.Dir(execPath)
		if stdruntime.GOOS != "windows" && strings.Contains(execDir, "AdbAutoPlayer.app") {
			execDir = filepath.Dir(filepath.Dir(filepath.Dir(filepath.Dir(execPath)))) // Go outside the .app bundle
		}
		if err := os.Chdir(execDir); err != nil {
			panic(fmt.Sprintf("Failed to change working directory to %s: %v", execDir, err))
		}
	}

	_, err = os.Getwd()
	if err != nil {
		panic(err)
	}
}
