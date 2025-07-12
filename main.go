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
	"github.com/wailsapp/wails/v3/pkg/events"
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
			application.NewService(settings.Get()),
			application.NewService(&hotkeys.HotkeysService{}),
			application.NewService(updater.NewUpdateService(Version, isDev)),
			application.NewService(games.NewGamesService(isDev)),
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
			process.Get().KillProcess()
		},
	})

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
		BackgroundColour: application.NewRGB(27, 38, 54),
		URL:              "/",
	})

	_ = buildSpotifyesqueSystemTray(
		app,
		window,
	)

	err := app.Run()
	if err != nil {
		log.Fatal(err)
	}
}

func buildSpotifyesqueSystemTray(app *application.App, window *application.WebviewWindow) *application.SystemTray {
	systemTray := app.SystemTray.New()
	systemTray.SetLabel(app.Config().Name)
	systemTray.SetTooltip(app.Config().Name)

	// Do nothing
	systemTray.OnClick(func() {})

	systemTray.OnDoubleClick(func() {
		window.Show()
		window.Focus()
	})

	menu := app.NewMenu()
	systemTray.SetMenu(menu)

	minimizeToTray := menu.Add("Minimize to Tray")
	minimizeToTray.SetHidden(true)
	minimizeToTray.OnClick(func(context *application.Context) {
		window.Hide()
	})

	showApp := menu.Add("Show " + app.Config().Name)
	showApp.SetHidden(true)
	showApp.OnClick(func(context *application.Context) {
		window.Show()
		window.Focus()
	})

	menu.Add("Exit").OnClick(func(context *application.Context) {
		app.Quit()
	})

	window.RegisterHook(events.Common.WindowHide, func(e *application.WindowEvent) {
		minimizeToTray.SetHidden(true)
		showApp.SetHidden(false)
	})

	window.RegisterHook(events.Common.WindowClosing, func(e *application.WindowEvent) {
		if settings.Get().GetGeneralSettings().UI.CloseShouldMinimize {
			e.Cancel()
			window.Hide()
		}
	})

	window.RegisterHook(events.Common.WindowShow, func(e *application.WindowEvent) {
		minimizeToTray.SetHidden(false)
		showApp.SetHidden(true)
	})

	// Without this the window minimizes to systray when focus is lost
	window.RegisterHook(events.Common.WindowLostFocus, func(e *application.WindowEvent) {
		e.Cancel()
	})

	return systemTray
}

// func addNotifier(app *application.App) {
// 	notifier := notifications.New()
// 	app.RegisterService(application.NewService(notifier))
// }
