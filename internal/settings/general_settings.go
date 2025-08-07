package settings

import (
	"adb-auto-player/internal/ipc"
	"github.com/pelletier/go-toml/v2"
	"os"
)

type GeneralSettings struct {
	Advanced AdvancedSettings `toml:"advanced" json:"Advanced"`
	Device   DeviceSettings   `toml:"device"`
	Update   UpdateSettings   `toml:"update"`
	Logging  LoggingSettings  `toml:"logging"`
	UI       UISettings       `toml:"ui" json:"User Interface"`
}

type DeviceSettings struct {
	ID               string `toml:"ID"`
	UseWMResize      bool   `toml:"wm_size" json:"Resize Display (Phone/Tablet only)"`
	Streaming        bool   `toml:"streaming" json:"Device Streaming (disable for slow PCs)"`
	HardwareDecoding bool   `toml:"hardware_decoding" json:"Enable Hardware Decoding"`
}

type AdvancedSettings struct {
	ADBHost        string `toml:"host" json:"ADB Server Host"`
	ADBPort        int    `toml:"port" json:"ADB Server Port"`
	AutoPlayerHost string `toml:"auto_player_host" json:"AutoPlayer Host"`
	AutoPlayerPort int    `toml:"auto_player_port" json:"AutoPlayer Port"`
	StreamingFPS   int    `toml:"streaming_fps" json:"Streaming FPS"`
}

type UpdateSettings struct {
	AutoUpdate         bool `toml:"auto_updates" json:"Automatically download updates"`
	EnableAlphaUpdates bool `toml:"enable_alpha_updates" json:"Download Alpha updates"`
}

type LoggingSettings struct {
	Level                string `toml:"level" json:"Log Level"`
	DebugSaveScreenshots int    `toml:"debug_save_screenshots" json:"Debug Screenshot Limit"`
	TaskLogLimit         int    `toml:"action_log_limit" json:"Task Log Limit"`
}

type UISettings struct {
	Theme                string `toml:"theme"`
	Locale               string `toml:"locale" json:"Language"`
	CloseShouldMinimize  bool   `toml:"close_should_minimize" json:"Close button should minimize the window"`
	NotificationsEnabled bool   `toml:"notifications_enabled" json:"Enable Notifications"`
}

func NewGeneralSettings() GeneralSettings {
	return GeneralSettings{
		Advanced: AdvancedSettings{
			ADBHost:        "127.0.0.1",
			ADBPort:        5037,
			AutoPlayerHost: "127.0.0.1",
			AutoPlayerPort: 62121,
			StreamingFPS:   30,
		},
		Device: DeviceSettings{
			ID:               "127.0.0.1:7555",
			UseWMResize:      false,
			Streaming:        true,
			HardwareDecoding: false,
		},
		Update: UpdateSettings{
			AutoUpdate:         false,
			EnableAlphaUpdates: false,
		},
		Logging: LoggingSettings{
			Level:                string(ipc.LogLevelInfo),
			DebugSaveScreenshots: 60,
			TaskLogLimit:         5,
		},
		UI: UISettings{
			Theme:                "catppuccin",
			Locale:               "en",
			CloseShouldMinimize:  false,
			NotificationsEnabled: false,
		},
	}
}

func LoadGeneralSettings(filePath string) (*GeneralSettings, error) {
	defaultConfig := NewGeneralSettings()

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
