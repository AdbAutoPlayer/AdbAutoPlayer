package games

type MenuOption struct {
	Label string
	Args  []string
}

type Game struct {
	GameTitle         string
	ConfigPath        string
	ExePath           string
	PackageNames      []string
	MenuOptions       []MenuOption
	ConfigConstraints map[string]interface{}
}
