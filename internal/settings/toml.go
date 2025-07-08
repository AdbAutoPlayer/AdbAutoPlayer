package settings

import (
	"github.com/pelletier/go-toml/v2"
	"os"
	"path/filepath"
	"regexp"
)

func LoadTOML[T any](filePath string) (*T, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var config T
	if err = toml.Unmarshal(data, &config); err != nil {
		return nil, err
	}
	return &config, nil
}

func SaveTOML[T any](filePath string, config *T) error {
	newConfigData, err := toml.Marshal(config)
	if err != nil {
		return err
	}

	// toml.Marshal converts ints to float e.g. 2 => 2.0 this reverts this...
	// it would also convert an intended 2.0 to 2 but that is never an issue
	configStr := string(newConfigData)
	modifiedConfigStr := regexp.MustCompile(`=(\s\d+)\.0(\s|$)`).ReplaceAllString(configStr, `=$1$2`)
	newConfigData = []byte(modifiedConfigStr)

	if err = os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
		return err
	}
	if err = os.WriteFile(filePath, newConfigData, 0644); err != nil {
		return err
	}

	return nil
}
