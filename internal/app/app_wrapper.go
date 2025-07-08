package app

import "github.com/wailsapp/wails/v3/pkg/application"

func EmitEvent(event *application.CustomEvent) {
	app := application.Get()
	if app != nil {
		application.Get().Event.EmitEvent(event)
	}
}
