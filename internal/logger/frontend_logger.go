package logger

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/path"
	"fmt"
	"github.com/wailsapp/wails/v3/pkg/application"
	"sync"
	"sync/atomic"
)

type FrontendLogger struct {
	logLevel  *atomic.Uint32
	sanitizer *path.PathSanitizer
}

var (
	logLevelMap = map[ipc.LogLevel]uint32{
		ipc.LogLevelDebug:   2,
		ipc.LogLevelInfo:    3,
		ipc.LogLevelWarning: 4,
		ipc.LogLevelError:   5,
		ipc.LogLevelFatal:   6,
	}

	instance *FrontendLogger
	once     sync.Once
)

func newFrontendLogger(level ipc.LogLevel) *FrontendLogger {
	a := new(atomic.Uint32)
	a.Store(logLevelMap[level])

	return &FrontendLogger{
		logLevel:  a,
		sanitizer: path.NewPathSanitizer(),
	}
}

func Get() *FrontendLogger {
	once.Do(func() {
		instance = newFrontendLogger(ipc.LogLevelError)
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
	if !l.shouldLog(level) {
		return
	}
	l.logMessage(ipc.NewLogMessage(level, fmt.Sprintf(format, a...)))
}

func (l *FrontendLogger) SetLogLevelFromString(logLevel string) {
	l.logLevel.Store(getLogLevelFromString(logLevel))
}

func (l *FrontendLogger) SetLogLevel(level uint32) {
	l.logLevel.Store(level)
}

func getLogLevelFromString(logLevel string) uint32 {
	switch logLevel {
	case string(ipc.LogLevelDebug):
		return logLevelMap[ipc.LogLevelDebug]
	case string(ipc.LogLevelWarning):
		return logLevelMap[ipc.LogLevelWarning]
	case string(ipc.LogLevelError):
		return logLevelMap[ipc.LogLevelError]
	case string(ipc.LogLevelFatal):
		return logLevelMap[ipc.LogLevelFatal]
	default:
		return logLevelMap[ipc.LogLevelInfo]
	}
}

func (l *FrontendLogger) shouldLog(level ipc.LogLevel) bool {
	return l.logLevel.Load() <= logLevelMap[level]
}

func (l *FrontendLogger) LogMessage(message ipc.LogMessage) {
	if !l.shouldLog(message.Level) {
		return
	}
	l.logMessage(message)
}

func (l *FrontendLogger) GetLogLevel() uint32 {
	return l.logLevel.Load()
}

func (l *FrontendLogger) logMessage(message ipc.LogMessage) {
	message.Message = l.sanitizer.SanitizePath(message.Message)
	app.EmitEvent(&application.CustomEvent{Name: event_names.LogMessage, Data: message})
}
