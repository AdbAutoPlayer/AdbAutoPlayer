//go:build !windows

package updater

import (
	"testing"
)

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
