package ipc

type Constraint interface{}

type NumberConstraint struct {
	Type         string  `json:"type"`
	Step         float64 `json:"step"`
	Minimum      int     `json:"minimum"`
	Maximum      int     `json:"maximum"`
	DefaultValue int     `json:"default_value"`
}

type CheckboxConstraint struct {
	Type         string `json:"type"`
	DefaultValue bool   `json:"default_value"`
}

type MultiCheckboxConstraint struct {
	Type         string   `json:"type"`
	Choices      []string `json:"choices"`
	DefaultValue []string `json:"default_value"`
}

type ImageCheckboxConstraint struct {
	Type         string   `json:"type"`
	Choices      []string `json:"choices"`
	DefaultValue []string `json:"default_value"`
}

type SelectConstraint struct {
	Type         string   `json:"type"`
	Choices      []string `json:"choices"`
	DefaultValue string   `json:"default_value"`
}

type TextConstraint struct {
	Type         string `json:"type"`
	Regex        string `json:"regex"`
	DefaultValue string `json:"default_value"`
}

func NewNumberConstraint(minimum *int, maximum *int, step *float64, defaultValue int) NumberConstraint {
	if minimum == nil {
		minimum = new(int)
		*minimum = 1
	}
	if maximum == nil {
		maximum = new(int)
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

func NewTextConstraint(regex *string, defaultValue string) TextConstraint {
	if regex == nil {
		regex = new(string)
	}
	return TextConstraint{
		Type:         "text",
		Regex:        *regex,
		DefaultValue: defaultValue,
	}
}

func GetMainConfigConstraints() map[string]interface{} {
	portMin := 1024
	portMax := 65535

	// Combine them into a map for use in the config
	return map[string]interface{}{
		"Device": map[string]interface{}{
			"ID":               NewTextConstraint(nil, "127.0.0.1:5555"),
			"Resize Display":   NewCheckboxConstraint(false),
			"Device Streaming": NewCheckboxConstraint(true),
			"Order": []string{
				"ID", "Device Streaming", "Resize Display",
			},
		},
		"ADB": map[string]interface{}{
			"Host": NewTextConstraint(nil, "127.0.0.1"),
			"Port": NewNumberConstraint(&portMin, &portMax, nil, 5037),
		},
		"Logging": map[string]interface{}{
			"Level": NewSelectConstraint([]string{
				string(LogLevelDebug),
				string(LogLevelInfo),
				string(LogLevelWarning),
				string(LogLevelError),
				string(LogLevelFatal),
			}, string(LogLevelInfo)),
			"Debug Screenshot Limit": NewNumberConstraint(nil, nil, nil, 30),
		},
		"Order": []string{
			"ADB", "Device", "Logging",
		},
	}
}
