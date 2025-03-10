package ipc

type MenuOption struct {
	Label    string   `json:"label"`
	Args     []string `json:"args"`
	Category string   `json:"category,omitempty"`
	Tooltip  string   `json:"tooltip,omitempty"`
}

type GameGUI struct {
	GameTitle   string                 `json:"game_title"`
	ConfigPath  string                 `json:"config_path"`
	MenuOptions []MenuOption           `json:"menu_options"`
	Categories  []string               `json:"categories,omitempty"`
	Constraints map[string]interface{} `json:"constraints"`
}
