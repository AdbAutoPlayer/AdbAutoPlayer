package config

import (
	"github.com/stretchr/testify/assert"
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	mainConfig, err := LoadConfig[MainConfig]("../../testdata/config/config.toml")
	if err != nil {
		t.Errorf("[Error LoadConfig()] %v", err)
		return
	}
	assert.Equal(t, "emulator-5554", mainConfig.Device.ID)
}

func TestSaveConfig(t *testing.T) {
	testFilePath := "test_config.toml"

	deleteFileIfExists(testFilePath, t)

	mainConfig := NewMainConfig()

	if err := SaveConfig[MainConfig](testFilePath, &mainConfig); err != nil {
		t.Errorf("[Error SaveConfig()] %v", err)
		return
	}

	if _, err := os.Stat(testFilePath); os.IsNotExist(err) {
		t.Errorf("[Error] File does not exist after SaveConfig")
		return
	}

	deleteFileIfExists(testFilePath, t)
}

func deleteFileIfExists(filePath string, t *testing.T) {
	if _, err := os.Stat(filePath); err == nil {
		err = os.Remove(filePath)
		if err != nil {
			t.Errorf("[Error removing existing test file] %v", err)
		}
	}
}
