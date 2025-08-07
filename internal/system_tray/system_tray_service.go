package system_tray

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/settings"
	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/events"
	"runtime"
)

type SystemTrayService struct {
	systemTray       *application.SystemTray
	appWindow        *application.WebviewWindow
	systemTrayWindow *application.WebviewWindow
}

func (s *SystemTrayService) MinimizeToTray() {
	if s.systemTray != nil {
		s.systemTrayWindow.Hide()
	}
	s.appWindow.Hide()
}

func (s *SystemTrayService) ShowWindow() {
	if s.systemTray != nil {
		s.systemTrayWindow.Hide()
	}
	s.appWindow.Show()
	s.appWindow.Focus()
}

func (s *SystemTrayService) Exit() {
	s.systemTrayWindow.Hide()
	app.Quit()
}

func NewSystemTrayService(app *application.App, appWindow *application.WebviewWindow) *SystemTrayService {
	if runtime.GOOS != "windows" {
		return &SystemTrayService{
			systemTray:       nil,
			appWindow:        nil,
			systemTrayWindow: nil,
		}
	}
	systemTray, systemTrayWindow := buildSystemTray(app, appWindow)
	return &SystemTrayService{
		systemTray:       systemTray,
		appWindow:        appWindow,
		systemTrayWindow: systemTrayWindow,
	}
}

func buildSystemTray(wailsApp *application.App, appWindow *application.WebviewWindow) (*application.SystemTray, *application.WebviewWindow) {
	systemTrayWindow := wailsApp.Window.NewWithOptions(application.WebviewWindowOptions{
		Width:                      200,
		Height:                     80,
		EnableDragAndDrop:          false,
		DisableResize:              true,
		Frameless:                  true,
		Hidden:                     true,
		DefaultContextMenuDisabled: true,
		StartState:                 application.WindowStateNormal,
		Windows: application.WindowsWindow{
			Theme:           application.Dark,
			DisableIcon:     true,
			HiddenOnTaskbar: true,
		},
		Mac: application.MacWindow{
			Backdrop: application.MacBackdropTranslucent,
			TitleBar: application.MacTitleBarHidden,
		},
		BackgroundColour: application.NewRGB(27, 38, 54),
		URL:              "/system-tray",
	})

	systemTray := wailsApp.SystemTray.New()
	systemTray.SetLabel(wailsApp.Config().Name)
	systemTray.SetTooltip(wailsApp.Config().Name)
	systemTray.AttachWindow(systemTrayWindow)
	systemTrayWindow.Hide()
	wailsApp.Window.Add(systemTrayWindow)

	// Do nothing
	systemTray.OnClick(func() {})

	systemTray.OnDoubleClick(func() {
		appWindow.Show()
		appWindow.Focus()
	})
	systemTray.OnRightClick(func() {
		if systemTrayWindow != nil {
			_ = systemTray.PositionWindow(systemTrayWindow, 5)
			systemTrayWindow.Show()
		}
	})

	appWindow.RegisterHook(events.Common.WindowHide, func(e *application.WindowEvent) {
		app.EmitEvent(&application.CustomEvent{
			Name: event_names.WindowIsVisible,
			Data: false,
		})
	})

	appWindow.RegisterHook(events.Common.WindowClosing, func(e *application.WindowEvent) {
		e.Cancel()
		if settings.GetService().GetGeneralSettings().UI.CloseShouldMinimize {
			appWindow.Hide()
			return
		}
		app.Quit()
	})

	appWindow.RegisterHook(events.Common.WindowShow, func(e *application.WindowEvent) {
		app.EmitEvent(&application.CustomEvent{
			Name: event_names.WindowIsVisible,
			Data: true,
		})
	})

	// Without this the window minimizes to systray when focus is lost
	appWindow.RegisterHook(events.Common.WindowLostFocus, func(e *application.WindowEvent) {
		e.Cancel()
	})

	return systemTray, systemTrayWindow
}
