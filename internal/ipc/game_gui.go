package ipc

type MenuOption struct {
	Label string   `json:"label"`
	Args  []string `json:"args"`
	Order int      `json:"order"`
}

type GameGUI struct {
	GameTitle   string                 `json:"game_title"`
	ConfigPath  string                 `json:"config_path"`
	MenuOptions []MenuOption           `json:"menu_options"`
	Constraints map[string]interface{} `json:"constraints"`
	Order       int                    `json:"order"`
}
