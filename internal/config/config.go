package config

import (
	"adb-auto-player/internal/ipc"
	"github.com/pelletier/go-toml/v2"
	"os"
	"path/filepath"
	"regexp"
)

type MainConfig struct {
	ADB     ADBConfig     `toml:"adb" json:"ADB (Advanced)"`
	Device  DeviceConfig  `toml:"device"`
	Update  UpdateConfig  `toml:"update"`
	Logging LoggingConfig `toml:"logging"`
	UI      UIConfig      `toml:"ui" json:"User Interface"`
}

type DeviceConfig struct {
	ID               string `toml:"ID"`
	UseWMResize      bool   `toml:"wm_size" json:"Resize Display (Phone/Tablet only)"`
	Streaming        bool   `toml:"streaming" json:"Device Streaming (disable for slow PCs)"`
	HardwareDecoding bool   `toml:"hardware_decoding" json:"Enable Hardware Decoding"`
}

type ADBConfig struct {
	Host string `toml:"host"`
	Port int    `toml:"port"`
}

type UpdateConfig struct {
	AutoUpdate         bool `toml:"auto_updates" json:"Automatically download updates"`
	EnableAlphaUpdates bool `toml:"enable_alpha_updates" json:"Download Alpha updates"`
}

type LoggingConfig struct {
	Level                string `toml:"level" json:"Log Level"`
	DebugSaveScreenshots int    `toml:"debug_save_screenshots" json:"Debug Screenshot Limit"`
	ActionLogLimit       int    `toml:"action_log_limit" json:"Action Log Limit"`
}

type UIConfig struct {
	Theme  string `toml:"theme"`
	Locale string `toml:"locale" json:"Language"`
}

func NewMainConfig() MainConfig {
	return MainConfig{
		ADB: ADBConfig{
			Host: "127.0.0.1",
			Port: 5037,
		},
		Device: DeviceConfig{
			ID:               "127.0.0.1:5555",
			UseWMResize:      false,
			Streaming:        true,
			HardwareDecoding: false,
		},
		Update: UpdateConfig{
			AutoUpdate:         false,
			EnableAlphaUpdates: false,
		},
		Logging: LoggingConfig{
			Level:                string(ipc.LogLevelInfo),
			DebugSaveScreenshots: 60,
			ActionLogLimit:       5,
		},
		UI: UIConfig{
			Theme:  "catppuccin",
			Locale: "en",
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
	if err = toml.Unmarshal(data, &config); err != nil {
		return nil, err
	}
	return &config, nil
}

func SaveConfig[T any](filePath string, config *T) error {
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
