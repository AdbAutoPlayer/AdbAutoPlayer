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
	"strings"
)

//go:embed all:frontend/build
var assets embed.FS

func main() {
	useProdPath := changeWorkingDirForProd()

	app := NewApp(useProdPath)

	logLevel := logger.DEBUG
	mainConfig, err := config.LoadConfig[config.MainConfig]("config.toml")
	if err == nil {
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
	}
	frontendLogger := ipc.NewFrontendLogger(uint8(logLevel))

	err = wails.Run(&options.App{
		Title:  "AdbAutoPlayer",
		Width:  1024,
		Height: 768,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		BackgroundColour: &options.RGBA{R: 0, G: 0, B: 0, A: 0},
		Windows: &windows.Options{
			WindowIsTranslucent:  true,
			WebviewIsTransparent: true,
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
		println("Error:", err.Error())
	}
}

func changeWorkingDirForProd() bool {
	for _, arg := range os.Args {
		if strings.Contains(arg, "wailsbindings") {
			return false
		}

	}

	execPath, err := os.Executable()
	if err != nil {
		panic(fmt.Sprintf("Unable to get executable path: %v", err))
	}

	if !strings.HasSuffix(execPath, "-dev.exe") {
		binaryDir := filepath.Dir(execPath)
		if err := os.Chdir(binaryDir); err != nil {
			panic(fmt.Sprintf("Failed to change working directory to %s: %v", binaryDir, err))
		}
		return true
	}

	return false
}
