package config

import (
	"adb-auto-player/internal/ipc"
	"fmt"
	"github.com/pelletier/go-toml/v2"
	"os"
	"path/filepath"
	"regexp"
)

type MainConfig struct {
	Device  DeviceConfig  `toml:"device"`
	ADB     ADBConfig     `toml:"adb"`
	Logging LoggingConfig `toml:"logging"`
}

type DeviceConfig struct {
	ID          string `toml:"ID"`
	UseWMResize bool   `toml:"wm_size" json:"Resize Display"`
	Streaming   bool   `toml:"streaming" json:"Device Streaming"`
}

type ADBConfig struct {
	Host string `toml:"host"`
	Port int    `toml:"port"`
}

type LoggingConfig struct {
	Level                string `toml:"level"`
	DebugSaveScreenshots int    `toml:"debug_save_screenshots" json:"Debug Screenshot Limit"`
	ActionLogLimit       int    `toml:"action_log_limit" json:"Action Log Limit"`
}

func NewMainConfig() MainConfig {
	return MainConfig{
		Device: DeviceConfig{
			ID:          "127.0.0.1:5555",
			UseWMResize: false,
			Streaming:   true,
		},
		ADB: ADBConfig{
			Host: "127.0.0.1",
			Port: 5037,
		},
		Logging: LoggingConfig{
			Level:                string(ipc.LogLevelInfo),
			DebugSaveScreenshots: 30,
			ActionLogLimit:       10,
		},
	}
}

func LoadMainConfig(filePath string) (*MainConfig, error) {
	defaultConfig := NewMainConfig()

	data, err := os.ReadFile(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return &defaultConfig, nil
		}
		return nil, err
	}

	config := defaultConfig

	if err = toml.Unmarshal(data, &config); err != nil {
		return nil, err
	}

	return &config, nil
}

func LoadConfig[T any](filePath string) (*T, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var config T
	if err := toml.Unmarshal(data, &config); err != nil {
		return nil, err
	}
	return &config, nil
}

func SaveConfig[T any](filePath string, config *T) error {
	fmt.Printf("Saving config to %s\n", filePath)
	fmt.Printf("Config: %+v\n", config)
	newConfigData, err := toml.Marshal(config)
	if err != nil {
		return err
	}

	// toml.Marshal converts ints to float e.g. 2 => 2.0 this reverts this...
	// it would also convert an intended 2.0 to 2 but that is never an issue
	configStr := string(newConfigData)
	modifiedConfigStr := regexp.MustCompile(`=(\s\d+)\.0(\s|$)`).ReplaceAllString(configStr, `=$1$2`)
	newConfigData = []byte(modifiedConfigStr)

	if err := os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
		return err
	}
	if err := os.WriteFile(filePath, newConfigData, 0644); err != nil {
		return err
	}

	return nil
}
