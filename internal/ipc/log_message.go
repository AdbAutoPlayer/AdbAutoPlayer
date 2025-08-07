package ipc

import (
	"time"
)

type LogLevel string

const (
	LogLevelDebug   LogLevel = "DEBUG"
	LogLevelInfo    LogLevel = "INFO"
	LogLevelWarning LogLevel = "WARNING"
	LogLevelError   LogLevel = "ERROR"
	LogLevelFatal   LogLevel = "FATAL"
)

type LogMessage struct {
	Level        LogLevel `json:"level"`
	Message      string   `json:"message"`
	Timestamp    string   `json:"timestamp"`
	SourceFile   *string  `json:"source_file"`
	FunctionName *string  `json:"function_name"`
	LineNumber   *int32   `json:"line_number"`
	HTMLClass    *string  `json:"html_class"`
}

func NewLogMessage(
	level LogLevel,
	message string,
) LogMessage {
	return LogMessage{
		Level:        level,
		Message:      message,
		Timestamp:    time.Now().UTC().Format("2006-01-02T15:04:05.000Z"),
		SourceFile:   nil,
		FunctionName: nil,
		LineNumber:   nil,
		HTMLClass:    nil,
	}
}
