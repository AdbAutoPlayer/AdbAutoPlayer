package config

import (
	"adb-auto-player/internal/ipc"
	"github.com/pelletier/go-toml/v2"
	"os"
)

type MainConfig struct {
	Device  DeviceConfig  `toml:"device"`
	ADB     ADBConfig     `toml:"adb"`
	Logging LoggingConfig `toml:"logging"`
}

type DeviceConfig struct {
	ID string `toml:"ID"`
}

type ADBConfig struct {
	Host string `toml:"host"`
	Port int    `toml:"port"`
}

type LoggingConfig struct {
	Level string `toml:"level"`
}

func NewMainConfig() MainConfig {
	return MainConfig{
		Device: DeviceConfig{
			ID: "emulator-5554",
		},
		ADB: ADBConfig{
			Host: "127.0.0.1",
			Port: 5037,
		},
		Logging: LoggingConfig{
			Level: string(ipc.LogLevelInfo),
		},
	}
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
	newConfigData, err := toml.Marshal(config)
	if err != nil {
		return err
	}

	if err := os.WriteFile(filePath, newConfigData, 0644); err != nil {
		return err
	}

	return nil
}
