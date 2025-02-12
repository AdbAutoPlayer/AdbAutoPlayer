package ipc

import (
	"context"
	"fmt"
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

type FrontendLogger struct {
	ctx       context.Context
	logLevel  uint8
	sanitizer *PathSanitizer
}

var logLevelPriority = map[LogLevel]uint8{
	LogLevelTrace:   1,
	LogLevelDebug:   2,
	LogLevelInfo:    3,
	LogLevelWarning: 4,
	LogLevelError:   5,
	LogLevelFatal:   6,
}

func (l *FrontendLogger) Startup(ctx context.Context) {
	l.ctx = ctx
}

func NewFrontendLogger(logLevel uint8) *FrontendLogger {
	return &FrontendLogger{
		logLevel:  logLevel,
		sanitizer: NewPathSanitizer(),
	}
}

func (l *FrontendLogger) SetLogLevelFromInt(logLevel uint8) {
	l.logLevel = logLevel
}

func (l *FrontendLogger) SetLogLevelFromIPCLogLevel(logLevel LogLevel) {
	l.logLevel = logLevelPriority[logLevel]
}

func GetLogLevelFromString(logLevel string) uint8 {
	switch logLevel {
	case string(LogLevelTrace):
		return logLevelPriority[LogLevelTrace]
	case string(LogLevelDebug):
		return logLevelPriority[LogLevelDebug]
	case string(LogLevelWarning):
		return logLevelPriority[LogLevelWarning]
	case string(LogLevelError):
		return logLevelPriority[LogLevelError]
	case string(LogLevelFatal):
		return logLevelPriority[LogLevelFatal]
	default:
		return logLevelPriority[LogLevelInfo]
	}
}

func (l *FrontendLogger) SetLogLevelFromString(logLevel string) {
	l.logLevel = GetLogLevelFromString(logLevel)
}

func (l *FrontendLogger) Print(message string) {
	l.buildLogMessage(LogLevelInfo, message)
}

func (l *FrontendLogger) Trace(message string) {
	l.buildLogMessage(LogLevelTrace, message)
}

func (l *FrontendLogger) Tracef(message string, args ...interface{}) {
	l.buildLogMessage(LogLevelTrace, fmt.Sprintf(message, args...))
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

func (l *FrontendLogger) Infof(format string, a ...any) {
	l.buildLogMessage(LogLevelInfo, fmt.Sprintf(format, a...))
}

func (l *FrontendLogger) Warning(message string) {
	l.buildLogMessage(LogLevelWarning, message)
}

func (l *FrontendLogger) Warningf(format string, a ...any) {
	l.buildLogMessage(LogLevelWarning, fmt.Sprintf(format, a...))
}

func (l *FrontendLogger) Error(message string) {
	l.buildLogMessage(LogLevelError, message)
}

func (l *FrontendLogger) Errorf(format string, a ...any) {
	l.buildLogMessage(LogLevelError, fmt.Sprintf(format, a...))
}

func (l *FrontendLogger) Fatal(message string) {
	l.buildLogMessage(LogLevelFatal, message)
}

func (l *FrontendLogger) Fatalf(format string, a ...any) {
	l.buildLogMessage(LogLevelFatal, fmt.Sprintf(format, a...))
}

func (l *FrontendLogger) buildLogMessage(level LogLevel, message string) {
	if l.ctx == nil {
		return
	}
	logMessage := NewLogMessage(level, message)

	l.LogMessage(logMessage)
}

func (l *FrontendLogger) LogMessage(message LogMessage) {
	if l.logLevel > logLevelPriority[message.Level] {
		return
	}
	message.Message = l.sanitizer.SanitizePath(message.Message)
	runtime.EventsEmit(l.ctx, "log-message", message)
}
