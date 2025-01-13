package ipc

import (
	"context"
	"fmt"
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

type FrontendLogger struct {
	ctx context.Context
}

func (l *FrontendLogger) Startup(ctx context.Context) {
	l.ctx = ctx
}

func NewFrontendLogger() *FrontendLogger {
	return &FrontendLogger{}
}

func (l *FrontendLogger) Print(message string) {
	l.buildLogMessage(LogLevelInfo, message)
}

func (l *FrontendLogger) Trace(message string) {
	l.buildLogMessage(LogLevelTrace, message)
}

func (l *FrontendLogger) Debug(message string) {
	l.buildLogMessage(LogLevelDebug, message)
}

func (l *FrontendLogger) Debugf(format string, a ...any) {
	l.buildLogMessage(LogLevelDebug, fmt.Sprintf(format, a...))
}

func (l *FrontendLogger) Info(message string) {
	l.buildLogMessage(LogLevelInfo, message)
}

func (l *FrontendLogger) Warning(message string) {
	l.buildLogMessage(LogLevelWarning, message)
}

func (l *FrontendLogger) Error(message string) {
	l.buildLogMessage(LogLevelError, message)
}

func (l *FrontendLogger) Fatal(message string) {
	l.buildLogMessage(LogLevelFatal, message)
}

func (l *FrontendLogger) buildLogMessage(level LogLevel, message string) {
	if l.ctx == nil {
		return
	}
	logMessage := NewLogMessage(level, message)

	l.LogMessage(logMessage)
}

func (l *FrontendLogger) LogMessage(message LogMessage) {
	runtime.EventsEmit(l.ctx, "log-message", message)
}
