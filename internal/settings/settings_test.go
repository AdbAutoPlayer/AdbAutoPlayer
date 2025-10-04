package settings

import (
	"testing"
)

func TestNewSettings(t *testing.T) {
	settings := NewSettings()
	if settings.Advanced.AutoPlayerPort != 62121 {
		t.Errorf("NewSettings did not return expected Advanced.AutoPlayerPort")
	}

	if settings.Device.HardwareDecoding != false {
		t.Errorf("settings.Device.HardwareDecoding did not return false")
	}
}

func TestLoadSettings(t *testing.T) {
	settings, err := LoadSettings("../../settings/AdbAutoPlayer.toml")
	if err != nil {
		t.Error(err)
	}

	if settings.Device.HardwareDecoding != true {
		t.Errorf("settings.Device.HardwareDecoding did not return true")
	}
}
