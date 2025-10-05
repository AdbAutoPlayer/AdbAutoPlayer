package log_reader

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"bufio"
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"

	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/events"
)

type LogReaderService struct {
	logReaderWindow        *application.WebviewWindow
	logReaderWindowOptions application.WebviewWindowOptions
}

func NewLogReaderService() *LogReaderService {
	return &LogReaderService{
		logReaderWindow: nil,
		logReaderWindowOptions: application.WebviewWindowOptions{
			Title:             "Log Reader",
			Width:             1168,
			Height:            776,
			EnableDragAndDrop: true,
			Windows: application.WindowsWindow{
				Theme: application.Dark,
			},
			Mac: application.MacWindow{
				Backdrop: application.MacBackdropTranslucent,
				TitleBar: application.MacTitleBarHidden,
			},
			BackgroundColour:   application.NewRGB(27, 38, 54),
			URL:                "/log-reader",
			ZoomControlEnabled: false,
		},
	}
}

func (s *LogReaderService) OpenLogReaderWindow() {
	if s.logReaderWindow == nil {
		s.createWindow()
	}

	s.logReaderWindow.Focus()
}

func (s *LogReaderService) createWindow() {
	s.logReaderWindow = application.Get().Window.NewWithOptions(s.logReaderWindowOptions)

	s.logReaderWindow.OnWindowEvent(events.Common.WindowDropZoneFilesDropped, func(event *application.WindowEvent) {
		// details := event.Context().DropZoneDetails()

		droppedFiles := event.Context().DroppedFiles()

		app.Emit(event_names.LogReaderClear)

		var logMessages []ipc.LogMessage
		for _, file := range droppedFiles {

			if filepath.Ext(file) != ".log" {
				app.EmitEvent(&application.CustomEvent{
					Name: event_names.LogReaderMessage,
					Data: ipc.NewLogMessagef(ipc.LogLevelError, "not a .log file %s", file),
				})
				continue
			}
			data, readErr := os.ReadFile(file)
			if readErr != nil {
				app.EmitEvent(&application.CustomEvent{
					Name: event_names.LogReaderMessage,
					Data: ipc.NewLogMessagef(ipc.LogLevelError, "failed to read file %s: %v\n", file, readErr),
				})
				continue
			}
			scanner := bufio.NewScanner(bytes.NewReader(data))
			for scanner.Scan() {
				line := scanner.Text()
				if strings.TrimSpace(line) == "" {
					continue
				}

				var msg ipc.LogMessage
				if err := json.Unmarshal([]byte(line), &msg); err != nil {
					app.EmitEvent(&application.CustomEvent{
						Name: event_names.LogReaderMessage,
						Data: ipc.NewLogMessagef(ipc.LogLevelError, "failed to parse line in %s: %v\n", file, err),
					})
					continue
				}

				logMessages = append(logMessages, msg)
			}

			if err := scanner.Err(); err != nil {
				app.EmitEvent(&application.CustomEvent{
					Name: event_names.LogReaderMessage,
					Data: ipc.NewLogMessagef(ipc.LogLevelError, "error reading file %s: %v\n", file, err),
				})
			}
		}

		app.EmitEvent(&application.CustomEvent{
			Name: event_names.LogReaderMessage,
			Data: logMessages,
		})
	})
	s.logReaderWindow.RegisterHook(events.Common.WindowClosing, func(e *application.WindowEvent) {
		s.logReaderWindow = nil
	})
}
