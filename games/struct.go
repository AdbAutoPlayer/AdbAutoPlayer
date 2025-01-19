package games

type MenuOption struct {
	Label string
	Args  []string
}

type Game struct {
	GameTitle         string
	ConfigPath        string
	BinaryPath        string
	PackageNames      []string
	MenuOptions       []MenuOption
	ConfigConstraints map[string]interface{}
}
