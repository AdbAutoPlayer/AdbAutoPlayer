package settings

import (
	"os"
	"path/filepath"
	"regexp"

	"github.com/pelletier/go-toml/v2"
)

func LoadTOML[T any](filePath string) (*T, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var settings T
	if err = toml.Unmarshal(data, &settings); err != nil {
		return nil, err
	}
	return &settings, nil
}

func SaveTOML[T any](filePath string, settings *T) error {
	newSettingsData, err := toml.Marshal(settings)
	if err != nil {
		return err
	}

	// toml.Marshal converts ints to float e.g. 2 => 2.0 this reverts this...
	// it would also convert an intended 2.0 to 2 but that is never an issue
	settingsStr := string(newSettingsData)
	modifiedSettingsStr := regexp.MustCompile(`=(\s\d+)\.0(\s|$)`).ReplaceAllString(settingsStr, `=$1$2`)
	newSettingsData = []byte(modifiedSettingsStr)

	if err = os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
		return err
	}
	if err = os.WriteFile(filePath, newSettingsData, 0644); err != nil {
		return err
	}

	return nil
}
