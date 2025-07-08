package logger

import (
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/path"
	"fmt"
	"github.com/wailsapp/wails/v3/pkg/application"
	"sync"
)

type FrontendLogger struct {
	LogLevel  uint8
	sanitizer *path.PathSanitizer
}

var (
	logLevelPriority = map[ipc.LogLevel]uint8{
		ipc.LogLevelDebug:   2,
		ipc.LogLevelInfo:    3,
		ipc.LogLevelWarning: 4,
		ipc.LogLevelError:   5,
		ipc.LogLevelFatal:   6,
	}

	instance *FrontendLogger
	once     sync.Once
)

func newFrontendLogger() *FrontendLogger {
	return &FrontendLogger{
		sanitizer: path.NewPathSanitizer(),
	}
}

func Get() *FrontendLogger {
	once.Do(func() {
		instance = newFrontendLogger()
	})
	return instance
}

func (l *FrontendLogger) Debugf(format string, a ...any) {
	l.buildLogMessage(ipc.LogLevelDebug, format, a...)
}

func (l *FrontendLogger) Infof(format string, a ...any) {
	l.buildLogMessage(ipc.LogLevelInfo, format, a...)
}

func (l *FrontendLogger) Warningf(format string, a ...any) {
	l.buildLogMessage(ipc.LogLevelWarning, format, a...)
}

func (l *FrontendLogger) Errorf(format string, a ...any) {
	l.buildLogMessage(ipc.LogLevelError, format, a...)
}

func (l *FrontendLogger) buildLogMessage(level ipc.LogLevel, format string, a ...any) {
	if l.LogLevel > logLevelPriority[level] {
		return
	}
	l.logMessage(ipc.NewLogMessage(level, fmt.Sprintf(format, a...)))
}

func (l *FrontendLogger) SetLogLevelFromString(logLevel string) {
	l.LogLevel = getLogLevelFromString(logLevel)
}

func getLogLevelFromString(logLevel string) uint8 {
	switch logLevel {
	case string(ipc.LogLevelDebug):
		return logLevelPriority[ipc.LogLevelDebug]
	case string(ipc.LogLevelWarning):
		return logLevelPriority[ipc.LogLevelWarning]
	case string(ipc.LogLevelError):
		return logLevelPriority[ipc.LogLevelError]
	case string(ipc.LogLevelFatal):
		return logLevelPriority[ipc.LogLevelFatal]
	default:
		return logLevelPriority[ipc.LogLevelInfo]
	}
}

func (l *FrontendLogger) LogMessage(message ipc.LogMessage) {
	if l.LogLevel > logLevelPriority[message.Level] {
		return
	}
	l.logMessage(message)
}

func (l *FrontendLogger) logMessage(message ipc.LogMessage) {
	message.Message = l.sanitizer.SanitizePath(message.Message)
	application.Get().Event.EmitEvent(&application.CustomEvent{Name: "log-message", Data: message})
}
