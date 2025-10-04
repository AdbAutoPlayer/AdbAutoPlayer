package ipc

type MenuOption struct {
	Label       string   `json:"label"`
	CustomLabel string   `json:"custom_label,omitempty"`
	Args        []string `json:"args"`
	Category    string   `json:"category,omitempty"`
	Tooltip     string   `json:"tooltip,omitempty"`
}

type GameGUI struct {
	GameTitle    string                 `json:"game_title"`
	SettingsFile string                 `json:"settings_file"`
	MenuOptions  []MenuOption           `json:"menu_options"`
	Categories   []string               `json:"categories,omitempty"`
	Constraints  map[string]interface{} `json:"constraints"`
}
