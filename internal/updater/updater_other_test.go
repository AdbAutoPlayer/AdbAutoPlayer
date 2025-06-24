//go:build !windows

package updater

import (
	"testing"
)

func TestUpdateManager_CheckForUpdates_NonWindows(t *testing.T) {
	tests := []struct {
		name               string
		isDev              bool
		autoUpdate         bool
		enableAlphaUpdates bool
		expectAvailable    bool
		expectError        bool
		expectedErrorMsg   string
	}{
		{
			name:               "dev mode returns no updates available",
			isDev:              true,
			autoUpdate:         false,
			enableAlphaUpdates: false,
			expectAvailable:    false,
			expectError:        false,
		},
		{
			name:               "dev mode with auto update enabled",
			isDev:              true,
			autoUpdate:         true,
			enableAlphaUpdates: false,
			expectAvailable:    false,
			expectError:        false,
		},
		{
			name:               "dev mode with alpha updates enabled",
			isDev:              true,
			autoUpdate:         false,
			enableAlphaUpdates: true,
			expectAvailable:    false,
			expectError:        false,
		},
		{
			name:               "dev mode with all options enabled",
			isDev:              true,
			autoUpdate:         true,
			enableAlphaUpdates: true,
			expectAvailable:    false,
			expectError:        false,
		},
		{
			name:               "production mode returns not implemented error",
			isDev:              false,
			autoUpdate:         false,
			enableAlphaUpdates: false,
			expectAvailable:    false,
			expectError:        true,
			expectedErrorMsg:   "not implemented",
		},
		{
			name:               "production mode with auto update",
			isDev:              false,
			autoUpdate:         true,
			enableAlphaUpdates: false,
			expectAvailable:    false,
			expectError:        true,
			expectedErrorMsg:   "not implemented",
		},
		{
			name:               "production mode with alpha updates",
			isDev:              false,
			autoUpdate:         false,
			enableAlphaUpdates: true,
			expectAvailable:    false,
			expectError:        true,
			expectedErrorMsg:   "not implemented",
		},
		{
			name:               "production mode with all options",
			isDev:              false,
			autoUpdate:         true,
			enableAlphaUpdates: true,
			expectAvailable:    false,
			expectError:        true,
			expectedErrorMsg:   "not implemented",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			um := &UpdateManager{
				isDev: tt.isDev,
			}

			result, err := um.CheckForUpdates(tt.autoUpdate, tt.enableAlphaUpdates)

			// Check error expectation
			if tt.expectError {
				if err == nil {
					t.Errorf("expected error but got none")
					return
				}
				if err.Error() != tt.expectedErrorMsg {
					t.Errorf("expected error message %q, got %q", tt.expectedErrorMsg, err.Error())
				}
			} else {
				if err != nil {
					t.Errorf("expected no error but got: %v", err)
					return
				}
			}

			// Check availability
			if result.Available != tt.expectAvailable {
				t.Errorf("expected Available to be %v, got %v", tt.expectAvailable, result.Available)
			}
		})
	}
}

func TestUpdateManager_DownloadAndApplyUpdate_NonWindows(t *testing.T) {
	tests := []struct {
		name             string
		downloadURL      string
		expectedErrorMsg string
	}{
		{
			name:             "empty URL returns not implemented error",
			downloadURL:      "",
			expectedErrorMsg: "not implemented",
		},
		{
			name:             "valid URL returns not implemented error",
			downloadURL:      "https://example.com/update.zip",
			expectedErrorMsg: "not implemented",
		},
		{
			name:             "invalid URL returns not implemented error",
			downloadURL:      "not-a-valid-url",
			expectedErrorMsg: "not implemented",
		},
		{
			name:             "local file path returns not implemented error",
			downloadURL:      "/path/to/local/file.zip",
			expectedErrorMsg: "not implemented",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			um := &UpdateManager{}

			err := um.DownloadAndApplyUpdate(tt.downloadURL)

			if err == nil {
				t.Error("expected error but got none")
				return
			}

			if err.Error() != tt.expectedErrorMsg {
				t.Errorf("expected error message %q, got %q", tt.expectedErrorMsg, err.Error())
			}
		})
	}
}

// Test that the methods exist and have the correct signatures
func TestUpdateManager_MethodSignatures_NonWindows(t *testing.T) {
	um := &UpdateManager{}

	// Test CheckForUpdates signature
	_, err := um.CheckForUpdates(false, false)
	if err == nil {
		t.Error("CheckForUpdates should return an error on non-Windows platforms in production mode")
	}

	// Test DownloadAndApplyUpdate signature
	err = um.DownloadAndApplyUpdate("test-url")
	if err == nil {
		t.Error("DownloadAndApplyUpdate should return an error on non-Windows platforms")
	}
}

// Benchmark tests to ensure the stub implementations are fast
func BenchmarkUpdateManager_CheckForUpdates_Dev_NonWindows(b *testing.B) {
	um := &UpdateManager{isDev: true}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = um.CheckForUpdates(false, false)
	}
}

func BenchmarkUpdateManager_CheckForUpdates_Prod_NonWindows(b *testing.B) {
	um := &UpdateManager{isDev: false}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = um.CheckForUpdates(false, false)
	}
}

func BenchmarkUpdateManager_DownloadAndApplyUpdate_NonWindows(b *testing.B) {
	um := &UpdateManager{}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = um.DownloadAndApplyUpdate("test-url")
	}
}
