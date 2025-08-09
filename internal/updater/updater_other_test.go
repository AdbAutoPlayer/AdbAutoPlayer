//go:build !windows

package updater

import (
	"testing"
)

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
