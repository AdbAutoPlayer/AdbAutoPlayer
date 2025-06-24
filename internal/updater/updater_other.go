//go:build !windows

package updater

import "fmt"

func (um *UpdateManager) CheckForUpdates(autoUpdate bool, enableAlphaUpdates bool) (UpdateInfo, error) {
	if um.isDev {
		return UpdateInfo{Available: false}, nil
	}

	return UpdateInfo{Available: false}, fmt.Errorf("not implemented")
}

func (um *UpdateManager) DownloadAndApplyUpdate(downloadURL string) error {
	return fmt.Errorf("not implemented")
}
