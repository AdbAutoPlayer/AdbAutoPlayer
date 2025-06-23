package ipc

import (
	"testing"
	"unicode/utf8"
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
			expected: `adb_path: C:\Users\$env:USERNAME\AppData\Local\file.txt`,
			runtime:  "windows",
			username: "testuser",
		},
		{
			name:     "macOS path",
			input:    "/Users/testuser/.config/file.txt",
			expected: "/Users/$USER/.config/file.txt",
			runtime:  "darwin",
			username: "testuser",
		},
		{
			name:     "Multiple Windows paths",
			input:    `adb_path: C:\Users\testuser\AppData\file.txt and D:\Users\testuser\Desktop\file2.txt`,
			expected: `adb_path: C:\Users\$env:USERNAME\AppData\file.txt and D:\Users\$env:USERNAME\Desktop\file2.txt`,
			runtime:  "windows",
			username: "testuser",
		},
		{
			name:     "Already redacted Windows",
			input:    `adb_path: C:\Users\$env:USERNAME\AppData\Local\file.txt`,
			expected: `adb_path: C:\Users\$env:USERNAME\AppData\Local\file.txt`,
			runtime:  "windows",
			username: "testuser",
		},
		{
			name:     "Already redacted macOS",
			input:    "adb_path: /Users/$USER/.config/file.txt",
			expected: "adb_path: /Users/$USER/.config/file.txt",
			runtime:  "darwin",
			username: "testuser",
		},
		{
			name:     "Username with special characters Windows",
			input:    `C:\Users\test.user\AppData\Local\file.txt`,
			expected: `C:\Users\$env:USERNAME\AppData\Local\file.txt`,
			runtime:  "windows",
			username: "test.user",
		},
		{
			name:     "Username with special characters macOS",
			input:    "/Users/test.user/.config/file.txt",
			expected: "/Users/$USER/.config/file.txt",
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

func TestNewPathSanitizer(t *testing.T) {
	t.Run("should create sanitizer with non-empty username", func(t *testing.T) {
		sanitizer := NewPathSanitizer()
		if sanitizer.username == "" {
			t.Error("Expected username to be non-empty, got empty string")
		}
		if !utf8.ValidString(sanitizer.username) {
			t.Errorf("Expected username to be valid UTF-8, got invalid string: %q", sanitizer.username)
		}
	})

	t.Run("should create unique usernames on each call", func(t *testing.T) {
		sanitizer1 := NewPathSanitizer()
		sanitizer2 := NewPathSanitizer()
		if sanitizer1.username == sanitizer2.username {
			t.Errorf("Expected unique usernames, got duplicates: %q", sanitizer1.username)
		}
	})

	t.Run("should create valid sanitizer instance", func(t *testing.T) {
		sanitizer := NewPathSanitizer()
		if sanitizer == nil {
			t.Error("Expected non-nil sanitizer instance, got nil")
		}
	})

}
