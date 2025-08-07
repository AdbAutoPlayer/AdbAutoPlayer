package main

import (
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/games"
	"adb-auto-player/internal/hotkeys"
	"adb-auto-player/internal/notifications"
	"adb-auto-player/internal/path"
	"adb-auto-player/internal/process"
	"adb-auto-player/internal/settings"
	"adb-auto-player/internal/system_tray"
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
	ipcService := process.GetService()
	ipcService.IsDev = isDev

	if !isDev {
		path.ChangeWorkingDirForProd()
	}

	app := application.New(application.Options{
		Name:        "AdbAutoPlayer",
		Description: "I'll add a description later",
		// This is for Wails system messages generally not interesting outside of dev.
		LogLevel: slog.LevelError,
		Services: []application.Service{
			application.NewService(settings.GetService()),
			application.NewService(&hotkeys.HotkeysService{}),
			application.NewService(updater.NewUpdateService(Version, isDev)),
			application.NewService(&games.GamesService{}),
			application.NewService(notifications.GetService()),
		},
		Assets: application.AssetOptions{
			Handler: application.AssetFileServerFS(assets),
			// Really no need to log this
			DisableLogging: true,
		},
		Mac: application.MacOptions{
			ApplicationShouldTerminateAfterLastWindowClosed: true,
		},
		OnShutdown: func() {
			ipcService.Shutdown()
		},
	})

	initializeEventHandlers(app)

	window := app.Window.NewWithOptions(application.WebviewWindowOptions{
		Title:  "AdbAutoPlayer",
		Width:  1168,
		Height: 776,
		// This is for DnD outside the window
		EnableDragAndDrop: false,
		Windows: application.WindowsWindow{
			Theme: application.Dark,
		},
		Mac: application.MacWindow{
			InvisibleTitleBarHeight: 50,
			Backdrop:                application.MacBackdropTranslucent,
			TitleBar:                application.MacTitleBarDefault,
		},
		BackgroundColour:   application.NewRGB(27, 38, 54),
		URL:                "/app",
		ZoomControlEnabled: false,
	})

	systemTrayService := system_tray.NewSystemTrayService(app, window)
	app.RegisterService(application.NewService(systemTrayService))

	err := app.Run()
	if err != nil {
		log.Fatal(err)
	}
}

func initializeEventHandlers(app *application.App) {
	if nil == app {
		return
	}

	app.Event.On(event_names.ServerAddressChanged, func(event *application.CustomEvent) {
		process.GetService().Shutdown()
	})
	app.Event.On(event_names.GeneralSettingsUpdated, func(event *application.CustomEvent) {
		process.GetService().InitializeManager()
		_, _ = process.GetService().SendPOST("/general-settings-updated", nil)
	})
	app.Event.On(event_names.GameSettingsUpdated, func(event *application.CustomEvent) {
		_, _ = process.GetService().SendPOST("/game-settings-updated", nil)
	})
}
