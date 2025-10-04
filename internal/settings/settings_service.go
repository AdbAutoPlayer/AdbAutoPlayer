package settings

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/path"
	"os"
	"path/filepath"
	"runtime"
	"sync"

	"github.com/wailsapp/wails/v3/pkg/application"
)

var (
	instance *SettingsService
	once     sync.Once
)

type SettingsService struct {
	adbAutoPlayerSettings AdbAutoPlayerSettings
	settingsDirPath       *string
	mu                    sync.RWMutex
}

// GetService returns the singleton instance of SettingsService
func GetService() *SettingsService {
	SettingsDirPath := resolveSettingsDirPath()
	once.Do(func() {
		instance = &SettingsService{
			settingsDirPath:       &SettingsDirPath,
			adbAutoPlayerSettings: loadAdbAutoPlayerSettingsOrDefault(&SettingsDirPath),
		}
	})
	return instance
}

// LoadSettings reloads the general settings
func (s *SettingsService) LoadAdbAutoPlayerSettings() AdbAutoPlayerSettings {
	s.mu.Lock()
	generalSettings := loadAdbAutoPlayerSettingsOrDefault(s.settingsDirPath)
	s.adbAutoPlayerSettings = generalSettings
	s.mu.Unlock()
	updateLogLevel(generalSettings.Logging.Level)
	return generalSettings
}

// GetAdbAutoPlayerSettings returns the current general settings
func (s *SettingsService) GetAdbAutoPlayerSettings() AdbAutoPlayerSettings {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.adbAutoPlayerSettings
}

func (s *SettingsService) GetAdbAutoPlayerSettingsForm() map[string]interface{} {
	generalSettings := s.LoadAdbAutoPlayerSettings()

	response := map[string]interface{}{
		"settings":    generalSettings,
		"constraints": ipc.GetAdbAutoPlayerSettingsConstraints(),
	}
	return response
}

func (s *SettingsService) SaveAdbAutoPlayerSettings(settings AdbAutoPlayerSettings) error {
	s.mu.Lock()

	settingsFile := filepath.Join(*s.settingsDirPath, "AdbAutoPlayer.toml")

	if err := SaveTOML[AdbAutoPlayerSettings](settingsFile, &settings); err != nil {
		s.mu.Unlock()
		app.Error(err.Error())
		return err
	}

	old := s.adbAutoPlayerSettings.Advanced
	if old.AutoPlayerHost != settings.Advanced.AutoPlayerHost || old.AutoPlayerPort != settings.Advanced.AutoPlayerPort {
		app.Emit(event_names.ServerAddressChanged)
	}

	s.adbAutoPlayerSettings = settings
	updateLogLevel(s.adbAutoPlayerSettings.Logging.Level)
	s.mu.Unlock()

	if settings.UI.NotificationsEnabled && runtime.GOOS != "windows" {
		logger.Get().Warningf("Setting: 'Enable Notifications' only works on Windows")
	}
	if settings.UI.CloseShouldMinimize && runtime.GOOS != "windows" {
		logger.Get().Warningf("Setting: 'Close button should minimize the window' only works on Windows")
	}

	app.EmitEvent(&application.CustomEvent{Name: event_names.AdbAutoPlayerSettingsUpdated, Data: settings})
	logger.Get().Infof("Saved General Settings")
	return nil
}

func (s *SettingsService) GetSettingsDirPath() string {
	if nil != s.settingsDirPath {
		return *s.settingsDirPath
	}

	return resolveSettingsDirPath()
}

func updateLogLevel(logLevel string) {
	logger.Get().SetLogLevelFromString(logLevel)
}

func loadAdbAutoPlayerSettingsOrDefault(settingsDirPath *string) AdbAutoPlayerSettings {
	generalSettings := NewSettings()

	if settingsDirPath != nil {
		settingsFile := filepath.Join(*settingsDirPath, "AdbAutoPlayer.toml")
		loadedSettings, err := LoadSettings(settingsFile)
		if err != nil {
			app.Error(err.Error())
		} else {
			generalSettings = *loadedSettings
			updateLogLevel(generalSettings.Logging.Level)
		}
	}

	return generalSettings
}

func resolveSettingsDirPath() string {
	paths := []string{
		"settings/", // dev, Windows
	}

	if runtime.GOOS == "darwin" {
		home, _ := os.UserHomeDir()
		macPath := filepath.Join(home, "Library/Application Support/AdbAutoPlayer/settings/")
		paths = append([]string{macPath}, paths...)
	}

	settingsPath := path.GetFirstPathThatExists(paths)
	if settingsPath == "" {
		return paths[0]
	}

	return settingsPath
}
