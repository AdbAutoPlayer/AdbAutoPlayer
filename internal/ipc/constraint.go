package ipc

type Constraint interface{}

type NumberConstraint struct {
	Type         string  `json:"type"`
	Step         float64 `json:"step"`
	Minimum      float64 `json:"minimum"`
	Maximum      float64 `json:"maximum"`
	DefaultValue float64 `json:"default_value"`
}

type CheckboxConstraint struct {
	Type         string `json:"type"`
	DefaultValue bool   `json:"default_value"`
}

type SelectConstraint struct {
	Type         string   `json:"type"`
	Choices      []string `json:"choices"`
	DefaultValue string   `json:"default_value"`
}

type TextConstraint struct {
	Type         string `json:"type"`
	Regex        string `json:"regex"`
	Title        string `json:"title"`
	DefaultValue string `json:"default_value"`
}

func NewNumberConstraint(minimum *float64, maximum *float64, step *float64, defaultValue float64) NumberConstraint {
	if minimum == nil {
		minimum = new(float64)
		*minimum = 1
	}
	if maximum == nil {
		maximum = new(float64)
		*maximum = 999
	}
	if step == nil {
		step = new(float64)
		*step = 1.0
	}
	return NumberConstraint{
		Type:         "number",
		Step:         *step,
		Minimum:      *minimum,
		Maximum:      *maximum,
		DefaultValue: defaultValue,
	}
}

func NewCheckboxConstraint(defaultValue bool) *CheckboxConstraint {
	return &CheckboxConstraint{
		Type:         "checkbox",
		DefaultValue: defaultValue,
	}
}

func NewSelectConstraint(choices []string, defaultValue string) SelectConstraint {
	return SelectConstraint{
		Type:         "select",
		Choices:      choices,
		DefaultValue: defaultValue,
	}
}

func NewTextConstraint(defaultValue string) TextConstraint {
	regex := new(string)
	title := new(string)

	return TextConstraint{
		Type:         "text",
		Regex:        *regex,
		Title:        *title,
		DefaultValue: defaultValue,
	}
}

func GetMainConfigConstraints() map[string]interface{} {
	portMin := 1024.0
	portMax := 65535.0
	minZero := 0.0

	return map[string]interface{}{
		"Device": map[string]interface{}{
			"ID": NewTextConstraint("127.0.0.1:5555"),
			"Device Streaming (disable for slow PCs)": NewCheckboxConstraint(true),
			"Enable Hardware Decoding":                NewCheckboxConstraint(false),
			"Resize Display (Phone/Tablet only)":      NewCheckboxConstraint(false),
			"Order": []string{
				"ID",
				"Device Streaming (disable for slow PCs)",
				"Enable Hardware Decoding",
				"Resize Display (Phone/Tablet only)",
			},
		},
		"ADB": map[string]interface{}{
			"Host": NewTextConstraint("127.0.0.1"),
			"Port": NewNumberConstraint(&portMin, &portMax, nil, 5037),
		},
		"Update": map[string]interface{}{
			"Automatically download updates": NewCheckboxConstraint(false),
			"Download Alpha updates":         NewCheckboxConstraint(false),
		},
		"Logging": map[string]interface{}{
			"Level": NewSelectConstraint([]string{
				string(LogLevelDebug),
				string(LogLevelInfo),
				string(LogLevelWarning),
				string(LogLevelError),
				string(LogLevelFatal),
			}, string(LogLevelInfo)),
			"Debug Screenshot Limit": NewNumberConstraint(&minZero, nil, nil, 60),
			"Action Log Limit":       NewNumberConstraint(&minZero, nil, nil, 5),
		},
		"User Interface": map[string]interface{}{
			"Theme": NewSelectConstraint([]string{
				"catppuccin",
				"cerberus",
				"crimson",
				"fennec",
				"hamlindigo",
				"legacy",
				"mint",
				"modern",
				"mona",
				"nosh",
				"nouveau",
				"pine",
				"reign",
				"rocket",
				"rose",
				"sahara",
				"seafoam",
				"terminus",
				"vintage",
				"vox",
				"wintry",
			}, "catppuccin"),
		},
		"Order": []string{
			"ADB", "Device", "Update", "Logging", "User Interface",
		},
	}
}
