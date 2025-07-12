package settings

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/path"
	"sync"
)

var (
	instance *SettingsService
	once     sync.Once
)

type SettingsService struct {
	generalSettings     GeneralSettings
	generalSettingsPath *string
}

// Get returns the singleton instance of SettingsService
func Get() *SettingsService {
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
	s.generalSettings = loadGeneralSettingsOrDefault(s.generalSettingsPath)
	updateLogLevel(s.generalSettings.Logging.Level)
	return s.GetGeneralSettings()
}

// GetGeneralSettings returns the current general settings
func (s *SettingsService) GetGeneralSettings() GeneralSettings {
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
	if err := SaveTOML[GeneralSettings](*s.generalSettingsPath, &settings); err != nil {
		app.Error(err.Error())
		return err
	}
	s.generalSettings = settings
	app.Emit("log-clear")
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
	if settingsPath == nil {
		return paths[0]
	}

	return *settingsPath
}
