package ipc

import (
	"testing"
)

func TestSanitizePath(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
		runtime  string
		username string
	}{
		{
			name:     "Windows path",
			input:    `adb_path: C:\Users\testuser\AppData\Local\file.txt`,
			expected: `adb_path: C:\Users\<redacted>\AppData\Local\file.txt`,
			runtime:  "windows",
			username: "testuser",
		},
		{
			name:     "macOS path",
			input:    "/Users/testuser/.config/file.txt",
			expected: "/Users/<redacted>/.config/file.txt",
			runtime:  "darwin",
			username: "testuser",
		},
		{
			name:     "Multiple Windows paths",
			input:    `adb_path: C:\Users\testuser\AppData\file.txt and D:\Users\testuser\Desktop\file2.txt`,
			expected: `adb_path: C:\Users\<redacted>\AppData\file.txt and D:\Users\<redacted>\Desktop\file2.txt`,
			runtime:  "windows",
			username: "testuser",
		},
		{
			name:     "Already redacted Windows",
			input:    `adb_path: C:\Users\<redacted>\AppData\Local\file.txt`,
			expected: `adb_path: C:\Users\<redacted>\AppData\Local\file.txt`,
			runtime:  "windows",
			username: "testuser",
		},
		{
			name:     "Already redacted macOS",
			input:    "adb_path: /Users/<redacted>/.config/file.txt",
			expected: "adb_path: /Users/<redacted>/.config/file.txt",
			runtime:  "darwin",
			username: "testuser",
		},
		{
			name:     "Username with special characters Windows",
			input:    `C:\Users\test.user\AppData\Local\file.txt`,
			expected: `C:\Users\<redacted>\AppData\Local\file.txt`,
			runtime:  "windows",
			username: "test.user",
		},
		{
			name:     "Username with special characters macOS",
			input:    "/Users/test.user/.config/file.txt",
			expected: "/Users/<redacted>/.config/file.txt",
			runtime:  "darwin",
			username: "test.user",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			sanitizer := NewPathSanitizerWithConfig(tt.runtime, tt.username)
			result := sanitizer.SanitizePath(tt.input)
			if result != tt.expected {
				t.Errorf("sanitizePath() = %v, want %v", result, tt.expected)
			}
		})
	}
}
