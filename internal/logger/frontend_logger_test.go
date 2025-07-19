package logger

import (
	"adb-auto-player/internal/ipc"
	"testing"
)

func TestFrontendLoggerSingleton(t *testing.T) {
	logger1 := Get()
	logger2 := Get()

	if logger1 != logger2 {
		t.Error("Get() should return the same instance")
	}
}

func TestLogLevelFromString(t *testing.T) {
	tests := []struct {
		input    string
		expected uint32
	}{
		{string(ipc.LogLevelDebug), logLevelMap[ipc.LogLevelDebug]},
		{string(ipc.LogLevelInfo), logLevelMap[ipc.LogLevelInfo]},
		{string(ipc.LogLevelWarning), logLevelMap[ipc.LogLevelWarning]},
		{string(ipc.LogLevelError), logLevelMap[ipc.LogLevelError]},
		{string(ipc.LogLevelFatal), logLevelMap[ipc.LogLevelFatal]},
		{"unknown", logLevelMap[ipc.LogLevelInfo]},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			logger := Get()
			logger.SetLogLevelFromString(tt.input)
			if logger.GetLogLevel() != tt.expected {
				t.Errorf("Expected level %d for input %s, got %d", tt.expected, tt.input, logger.logLevel)
			}
		})
	}
}

func TestShouldLog(t *testing.T) {
	tests := []struct {
		name      string
		setLevel  string
		testLevel ipc.LogLevel
		expected  bool
	}{
		{"Debug with Debug level", string(ipc.LogLevelDebug), ipc.LogLevelDebug, true},
		{"Info with Debug level", string(ipc.LogLevelDebug), ipc.LogLevelInfo, true},
		{"Debug with Info level", string(ipc.LogLevelInfo), ipc.LogLevelDebug, false},
		{"Info with Info level", string(ipc.LogLevelInfo), ipc.LogLevelInfo, true},
		{"Warning with Info level", string(ipc.LogLevelInfo), ipc.LogLevelWarning, true},
		{"Error with Warning level", string(ipc.LogLevelWarning), ipc.LogLevelError, true},
		{"Warning with Error level", string(ipc.LogLevelError), ipc.LogLevelWarning, false},
		{"Fatal with Error level", string(ipc.LogLevelError), ipc.LogLevelFatal, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			logger := Get()
			logger.SetLogLevelFromString(tt.setLevel)
			result := logger.shouldLog(tt.testLevel)
			if result != tt.expected {
				t.Errorf("%s: expected %v, got %v", tt.name, tt.expected, result)
			}
		})
	}
}

func TestLogMethods(t *testing.T) {
	// These tests just verify the methods don't panic
	// Actual output can't be easily tested without mocking the app.EmitEvent
	logger := Get()
	logger.SetLogLevelFromString(string(ipc.LogLevelDebug)) // Enable all levels

	logger.Debugf("test debug %s", "message")
	logger.Infof("test info %s", "message")
	logger.Warningf("test warning %s", "message")
	logger.Errorf("test error %s", "message")

	// Test LogMessage directly
	logger.LogMessage(ipc.LogMessage{
		Level:   ipc.LogLevelInfo,
		Message: "direct log message",
	})
}
