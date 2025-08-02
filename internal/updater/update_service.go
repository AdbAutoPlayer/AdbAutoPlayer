package updater

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/settings"
	"github.com/wailsapp/wails/v3/pkg/application"
)

type UpdateService struct {
	updateManager UpdateManager
}

func NewUpdateService(currentVersion string, isDev bool) *UpdateService {
	return &UpdateService{
		updateManager: NewUpdateManager(currentVersion, isDev),
	}
}

func (u *UpdateService) CheckForUpdates() (UpdateInfo, error) {
	updateSettings := settings.GetService().GetGeneralSettings().Update

	return u.updateManager.CheckForUpdates(updateSettings.AutoUpdate, updateSettings.EnableAlphaUpdates)
}

func (u *UpdateService) GetChangelogs() []Changelog {
	return u.updateManager.GetChangelogs()
}

func (u *UpdateService) DownloadUpdate(downloadURL string) error {
	u.updateManager.SetProgressCallback(func(progress float64) {
		app.EmitEvent(&application.CustomEvent{Name: event_names.DownloadProgress, Data: progress})
	})

	return u.updateManager.DownloadAndApplyUpdate(downloadURL)
}
