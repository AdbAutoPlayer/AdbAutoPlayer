package settings

import (
	"github.com/stretchr/testify/assert"
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	mainConfig, err := LoadTOML[GeneralSettings]("../../config/config.toml")
	if err != nil {
		t.Errorf("[Error LoadTOML()] %v", err)
		return
	}
	assert.Equal(t, "127.0.0.1:7555", mainConfig.Device.ID)
}

func TestSaveConfig(t *testing.T) {
	testFilePath := "test_config.toml"

	deleteFileIfExists(testFilePath, t)

	mainConfig := NewGeneralSettings()

	if err := SaveTOML[GeneralSettings](testFilePath, &mainConfig); err != nil {
		t.Errorf("[Error SaveTOML()] %v", err)
		return
	}

	if _, err := os.Stat(testFilePath); os.IsNotExist(err) {
		t.Errorf("[Error] File does not exist after SaveTOML")
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
