package afkjourney

import (
	"adb-auto-player/games"
	"adb-auto-player/internal/ipc"
)

type Config struct {
	General      GeneralConfig      `toml:"general"      json:"General"`
	AFKStages    AFKStagesConfig    `toml:"afk_stages"   json:"AFK Stages"`
	DurasTrials  DurasTrialsConfig  `toml:"duras_trials" json:"Duras Trials"`
	LegendTrials LegendTrialsConfig `toml:"legend_trials" json:"Legend Trials"`
}

type GeneralConfig struct {
	ExcludedHeroes []string `toml:"excluded_heroes" json:"Excluded Heroes"`
	AssistLimit    int      `toml:"assist_limit"    json:"Assist Limit"`
}

type AFKStagesConfig struct {
	Attempts               int  `toml:"attempts"                 json:"Attempts"`
	Formations             int  `toml:"formations"               json:"Formations"`
	UseSuggestedFormations bool `toml:"use_suggested_formations" json:"Use suggested Formations"`
	PushBothModes          bool `toml:"push_both_modes"          json:"Push both modes"`
	SpendGold              bool `toml:"spend_gold"               json:"Spend Gold"`
}

type DurasTrialsConfig struct {
	Attempts               int  `toml:"attempts"                 json:"Attempts"`
	Formations             int  `toml:"formations"               json:"Formations"`
	UseSuggestedFormations bool `toml:"use_suggested_formations" json:"Use suggested Formations"`
	SpendGold              bool `toml:"spend_gold"               json:"Spend Gold"`
}

type LegendTrialsConfig struct {
	Attempts               int      `toml:"attempts"                 json:"Attempts"`
	Formations             int      `toml:"formations"               json:"Formations"`
	UseSuggestedFormations bool     `toml:"use_suggested_formations" json:"Use suggested Formations"`
	SpendGold              bool     `toml:"spend_gold"               json:"Spend Gold"`
	Towers                 []string `toml:"towers"                   json:"Towers"`
}

func NewAFKJourney(useProdPath bool) games.Game {
	configPath := "../../python/adb_auto_player/games/afk_journey/AFKJourney.toml"
	exePath := "../../python/adb_auto_player.exe"
	if useProdPath {
		configPath = "games/afk_journey/AFKJourney.toml"
		exePath = "games/adb_auto_player.exe"
	}
	return games.Game{
		GameTitle:  "AFK Journey",
		ConfigPath: configPath,
		ExePath:    exePath,
		PackageNames: []string{
			"com.farlightgames.igame.gp",
			"com.farlightgames.igame.gp.vn",
		},
		MenuOptions: []games.MenuOption{
			{
				Label: "Push Season Talent Stages",
				Args:  []string{"SeasonTalentStages"},
			},
			{
				Label: "Push AFK Stages",
				Args:  []string{"AFKStages"},
			},
			{
				Label: "Push Duras Trials",
				Args:  []string{"DurasTrials"},
			},
			{
				Label: "Battle (suggested Formations)",
				Args:  []string{"BattleSuggested"},
			},
			{
				Label: "Battle (current Formation)",
				Args:  []string{"Battle"},
			},
			{
				Label: "Assist Synergy & CC",
				Args:  []string{"AssistSynergyAndCC"},
			},
			{
				Label: "Push Legend Trials",
				Args:  []string{"LegendTrials"},
			},
		},
		ConfigConstraints: getAFKJourneyConfigConstraints(),
	}
}

func getAFKJourneyConfigConstraints() map[string]interface{} {
	maxFormations := 7
	return map[string]interface{}{
		"General": map[string]interface{}{
			"Excluded Heroes": ipc.NewMultiCheckboxConstraint([]string{
				"Alsa", "Antandra", "Arden", "Atalanta",
				"Berial", "Bonnie", "Brutus", "Bryon",
				"Callan", "Carolina", "Cassadee", "Cecia", "Cryonaia", "Cyran",
				"Damian", "Dionel", "Dunlingr",
				"Eironn", "Elijah & Lailah",
				"Fae", "Faramor", "Florabelle",
				"Gerda", "Granny Dahnie",
				"Harak", "Hewynn", "Hodgkin", "Hugin",
				"Igor",
				"Kafra", "Koko", "Korin", "Kruger",
				"Lenya", "Lily May", "Lorsan", "Lucca", "Lucius", "Ludovic", "Lumont", "Lyca",
				"Marilee", "Mikola", "Mirael",
				"Nara", "Niru",
				"Odie",
				"Phraesto",
				"Reinier", "Rhys", "Rowan",
				"Salazer", "Satrana", "Scarlita", "Seth", "Shakir", "Shemira", "Silvina", "Sinbad", "Smokey", "Sonja", "Soren",
				"Talene", "Tasi", "Temesia", "Thoran",
				"Ulmus",
				"Vala", "Valen", "Valka", "Viperian",
				"Walker",
			}),
			"Assist Limit": ipc.NewNumberConstraint(nil, nil, nil),
		},
		"AFK Stages": map[string]interface{}{
			"Attempts":                 ipc.NewNumberConstraint(nil, nil, nil),
			"Formations":               ipc.NewNumberConstraint(nil, &maxFormations, nil),
			"Use suggested Formations": ipc.NewCheckboxConstraint(),
			"Push both modes":          ipc.NewCheckboxConstraint(),
			"Spend Gold":               ipc.NewCheckboxConstraint(),
		},
		"Duras Trials": map[string]interface{}{
			"Attempts":                 ipc.NewNumberConstraint(nil, nil, nil),
			"Formations":               ipc.NewNumberConstraint(nil, &maxFormations, nil),
			"Use suggested Formations": ipc.NewCheckboxConstraint(),
			"Spend Gold":               ipc.NewCheckboxConstraint(),
		},
		"Legend Trials": map[string]interface{}{
			"Attempts":                 ipc.NewNumberConstraint(nil, nil, nil),
			"Formations":               ipc.NewNumberConstraint(nil, &maxFormations, nil),
			"Use suggested Formations": ipc.NewCheckboxConstraint(),
			"Spend Gold":               ipc.NewCheckboxConstraint(),
			"Towers": ipc.NewImageCheckboxConstraint([]string{
				"Lightbearer", "Wilder", "Mauler", "Graveborn",
			}),
		},
	}
}
