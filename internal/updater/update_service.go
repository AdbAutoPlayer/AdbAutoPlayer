package updater

import (
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/settings"
	"fmt"
)

type UpdateService struct {
	updateManager UpdateManager
}

func NewUpdateService() *UpdateService {
	return &UpdateService{
		updateManager: NewUpdateManager("11.3.2", false),
	}
}

func (u *UpdateService) CheckForUpdates() (UpdateInfo, error) {
	if u.updateManager.isDev {
		logger.Get().Debugf("Updater disabled in dev.")
		return UpdateInfo{Disabled: true}, nil
	}

	updateSettings := settings.GetService().GetAdbAutoPlayerSettings().Update

	return u.updateManager.CheckForUpdates(updateSettings.AutoUpdate, updateSettings.EnableAlphaUpdates)
}

func (u *UpdateService) GetChangelogs() []Changelog {
	return u.updateManager.GetChangelogs()
}

func (u *UpdateService) DownloadUpdate() error {
	return fmt.Errorf("not available")
}
