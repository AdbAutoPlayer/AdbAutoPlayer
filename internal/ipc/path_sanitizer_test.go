package ipc

import (
	"testing"
)

func TestSanitizePath(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		expected  string
		isWindows bool
		username  string
	}{
		{
			name:      "Windows path",
			input:     `adb_path: C:\Users\testuser\AppData\Local\file.txt`,
			expected:  `adb_path: C:\Users\<redacted>\AppData\Local\file.txt`,
			isWindows: true,
			username:  "testuser",
		},
		{
			name:      "Unix path",
			input:     "/home/testuser/.config/file.txt",
			expected:  "/home/<redacted>/.config/file.txt",
			isWindows: false,
			username:  "testuser",
		},
		{
			name:      "Multiple Windows paths",
			input:     `adb_path: C:\Users\testuser\AppData\file.txt and C:\Users\testuser\Desktop\file2.txt`,
			expected:  `adb_path: C:\Users\<redacted>\AppData\file.txt and C:\Users\<redacted>\Desktop\file2.txt`,
			isWindows: true,
			username:  "testuser",
		},
		{
			name:      "Already redacted Windows",
			input:     `adb_path: C:\Users\<redacted>\AppData\Local\file.txt`,
			expected:  `adb_path: C:\Users\<redacted>\AppData\Local\file.txt`,
			isWindows: true,
			username:  "testuser",
		},
		{
			name:      "Already redacted Unix",
			input:     "adb_path: /home/<redacted>/.config/file.txt",
			expected:  "adb_path: /home/<redacted>/.config/file.txt",
			isWindows: false,
			username:  "testuser",
		},
		{
			name:      "Username with special characters Windows",
			input:     `C:\Users\test.user\AppData\Local\file.txt`,
			expected:  `C:\Users\<redacted>\AppData\Local\file.txt`,
			isWindows: true,
			username:  "test.user",
		},
		{
			name:      "Username with special characters Unix",
			input:     "/home/test.user/.config/file.txt",
			expected:  "/home/<redacted>/.config/file.txt",
			isWindows: false,
			username:  "test.user",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			sanitizer := NewPathSanitizerWithConfig(tt.isWindows, tt.username)
			result := sanitizer.SanitizePath(tt.input)
			if result != tt.expected {
				t.Errorf("sanitizePath() = %v, want %v", result, tt.expected)
			}
		})
	}
}
