//go:build !windows

package updater

import "fmt"

func (um *UpdateManager) CheckForUpdates(autoUpdate bool, enableAlphaUpdates bool) UpdateInfo {
	if um.isDev {
		return UpdateInfo{Available: false}
	}

	return UpdateInfo{Available: false}
}

func (um *UpdateManager) DownloadAndApplyUpdate(downloadURL string) error {
	return fmt.Errorf("Function DownloadAndApplyUpdate not implemented.")
}
