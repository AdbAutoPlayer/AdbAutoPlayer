package ipc

import (
	"time"
)

type LogLevel string

const (
	LogLevelTrace   LogLevel = "TRACE"
	LogLevelDebug   LogLevel = "DEBUG"
	LogLevelInfo    LogLevel = "INFO"
	LogLevelWarning LogLevel = "WARNING"
	LogLevelError   LogLevel = "ERROR"
	LogLevelFatal   LogLevel = "FATAL"
)

type LogMessage struct {
	Level      LogLevel  `json:"level"`
	Message    string    `json:"message"`
	Timestamp  time.Time `json:"timestamp"`
	SourceFile *string   `json:"source_file"`
	LineNumber *int32    `json:"line_number"`
}

func NewLogMessage(
	level LogLevel,
	message string,
) LogMessage {
	now := time.Now()
	timestamp := &now
	return LogMessage{
		Level:      level,
		Message:    message,
		Timestamp:  *timestamp,
		SourceFile: nil,
		LineNumber: nil,
	}
}
