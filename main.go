package main

import (
	"adb-auto-player/internal/games"
	"adb-auto-player/internal/hotkeys"
	"adb-auto-player/internal/path"
	"adb-auto-player/internal/process"
	"adb-auto-player/internal/settings"
	"adb-auto-player/internal/updater"
	"embed"
	"github.com/wailsapp/wails/v3/pkg/application"
	"log"
	"log/slog"
)

//go:embed all:frontend/dist
var assets embed.FS

// Version is set at build time using -ldflags "-X main.Version=..."
var Version = "dev" // default fallback for local dev runs

func main() {
	println()
	println("Version:", Version)

	isDev := Version == "dev"
	process.Get().IsDev = isDev

	settingsService := settings.Get()

	if !isDev {
		path.ChangeWorkingDirForProd()
	}

	// TODO create notifier service that wraps around this
	// addNotifier(app)

	app := application.New(application.Options{
		Name:        "AdbAutoPlayer",
		Description: "I'll add a description later",
		// This is for Wails system messages generally not interesting outside of dev.
		LogLevel: slog.LevelError,
		Services: []application.Service{
			application.NewService(settingsService),
			application.NewService(&hotkeys.HotkeysService{}),
			application.NewService(updater.NewUpdateService(Version, isDev)),
			application.NewService(games.NewGamesService(isDev)),
		},
		Assets: application.AssetOptions{
			Handler: application.AssetFileServerFS(assets),
		},
		Mac: application.MacOptions{
			ApplicationShouldTerminateAfterLastWindowClosed: true,
		},
		OnShutdown: func() {
			process.Get().KillProcess()
		},
	})

	window := app.Window.NewWithOptions(application.WebviewWindowOptions{
		Title:  "AdbAutoPlayer",
		Width:  1168,
		Height: 776,
		// This is for DnD outside the window
		EnableDragAndDrop: false,
		Mac: application.MacWindow{
			InvisibleTitleBarHeight: 50,
			Backdrop:                application.MacBackdropTranslucent,
			TitleBar:                application.MacTitleBarDefault,
		},
		BackgroundColour: application.NewRGB(27, 38, 54),
		URL:              "/",
	})

	addSystemTray(app, window)

	err := app.Run()
	if err != nil {
		log.Fatal(err)
	}
}

func addSystemTray(app *application.App, window *application.WebviewWindow) {
	systray := app.SystemTray.New()
	systray.SetLabel("AdbAutoPlayer")
	systray.SetTooltip("AdbAutoPlayer")
	systray.AttachWindow(window)
}

// func addNotifier(app *application.App) {
// 	notifier := notifications.New()
// 	app.RegisterService(application.NewService(notifier))
// }
