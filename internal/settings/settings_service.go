package settings

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/path"
	"github.com/wailsapp/wails/v3/pkg/application"
	"runtime"
	"sync"
)

var (
	instance *SettingsService
	once     sync.Once
)

type SettingsService struct {
	generalSettings     GeneralSettings
	generalSettingsPath *string
	mu                  sync.RWMutex
}

// GetService returns the singleton instance of SettingsService
func GetService() *SettingsService {
	generalSettingsPath := resolveGeneralSettingsPath()
	once.Do(func() {
		instance = &SettingsService{
			generalSettingsPath: &generalSettingsPath,
			generalSettings:     loadGeneralSettingsOrDefault(&generalSettingsPath),
		}
	})
	return instance
}

// LoadGeneralSettings reloads the general settings
func (s *SettingsService) LoadGeneralSettings() GeneralSettings {
	s.mu.Lock()
	generalSettings := loadGeneralSettingsOrDefault(s.generalSettingsPath)
	s.generalSettings = generalSettings
	s.mu.Unlock()
	updateLogLevel(generalSettings.Logging.Level)
	return generalSettings
}

// GetGeneralSettings returns the current general settings
func (s *SettingsService) GetGeneralSettings() GeneralSettings {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.generalSettings
}

func (s *SettingsService) GetGeneralSettingsForm() map[string]interface{} {
	generalSettings := s.LoadGeneralSettings()

	response := map[string]interface{}{
		"settings":    generalSettings,
		"constraints": ipc.GetMainConfigConstraints(),
	}
	return response
}

func (s *SettingsService) SaveGeneralSettings(settings GeneralSettings) error {
	s.mu.Lock()
	if err := SaveTOML[GeneralSettings](*s.generalSettingsPath, &settings); err != nil {
		s.mu.Unlock()
		app.Error(err.Error())
		return err
	}

	old := s.generalSettings.Advanced
	if old.AutoPlayerHost != settings.Advanced.AutoPlayerHost || old.AutoPlayerPort != settings.Advanced.AutoPlayerPort {
		app.Emit(event_names.ServerAddressChanged)
	}

	s.generalSettings = settings
	updateLogLevel(s.generalSettings.Logging.Level)
	s.mu.Unlock()

	if settings.UI.NotificationsEnabled && runtime.GOOS != "windows" {
		logger.Get().Warningf("Setting: 'Enable Notifications' only works on Windows")
	}
	if settings.UI.CloseShouldMinimize && runtime.GOOS != "windows" {
		logger.Get().Warningf("Setting: 'Close button should minimize the window' only works on Windows")
	}

	app.EmitEvent(&application.CustomEvent{Name: event_names.GeneralSettingsUpdated, Data: settings})
	logger.Get().Infof("Saved General Settings")
	return nil
}

func updateLogLevel(logLevel string) {
	logger.Get().SetLogLevelFromString(logLevel)
}

func loadGeneralSettingsOrDefault(tomlPath *string) GeneralSettings {
	generalSettings := NewGeneralSettings()

	if tomlPath != nil {
		loadedSettings, err := LoadGeneralSettings(*tomlPath)
		if err != nil {
			app.Error(err.Error())
		} else {
			generalSettings = *loadedSettings
			updateLogLevel(generalSettings.Logging.Level)
		}
	}

	return generalSettings
}

func resolveGeneralSettingsPath() string {
	paths := []string{
		"config.toml",              // distributed
		"config/config.toml",       // dev
		"../../config/config.toml", // macOS dev no not a joke
	}

	settingsPath := path.GetFirstPathThatExists(paths)
	if settingsPath == "" {
		return paths[0]
	}

	return settingsPath
}
