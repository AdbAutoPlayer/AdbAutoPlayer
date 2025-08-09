//go:build !windows

package updater

import (
	"fmt"
)

func (u *UpdateManager) DownloadAndApplyUpdate(downloadURL string) error {
	return fmt.Errorf("not implemented")
}
