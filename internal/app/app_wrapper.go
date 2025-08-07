package app

import "github.com/wailsapp/wails/v3/pkg/application"

func EmitEvent(event *application.CustomEvent) {
	app := application.Get()
	if app != nil {
		app.Event.EmitEvent(event)
	}
}

func Emit(name string) {
	app := application.Get()
	if app != nil {
		app.Event.Emit(name)
	}
}

func Error(msg string, args ...any) {
	app := application.Get()
	if app != nil {
		app.Logger.Error(msg, args...)
	}
}

func Quit() {
	app := application.Get()
	if app != nil {
		app.Quit()
	}
}
