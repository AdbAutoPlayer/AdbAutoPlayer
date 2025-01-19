package ipc

type Constraint interface{}

type NumberConstraint struct {
	Type    string  `json:"type"`
	Step    float64 `json:"step"`
	Minimum int     `json:"minimum"`
	Maximum int     `json:"maximum"`
}

type CheckboxConstraint struct {
	Type string `json:"type"`
}

type MultiCheckboxConstraint struct {
	Type    string   `json:"type"`
	Choices []string `json:"choices"`
}

type ImageCheckboxConstraint struct {
	Type    string   `json:"type"`
	Choices []string `json:"choices"`
}

type SelectConstraint struct {
	Type    string   `json:"type"`
	Choices []string `json:"choices"`
}

func NewNumberConstraint(minimum *int, maximum *int, step *float64) NumberConstraint {
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
		Type:    "number",
		Step:    *step,
		Minimum: *minimum,
		Maximum: *maximum,
	}
}

func NewCheckboxConstraint() *CheckboxConstraint {
	return &CheckboxConstraint{
		Type: "checkbox",
	}
}

func NewMultiCheckboxConstraint(choices []string) MultiCheckboxConstraint {
	return MultiCheckboxConstraint{
		Type:    "multicheckbox",
		Choices: choices,
	}
}

func NewImageCheckboxConstraint(choices []string) ImageCheckboxConstraint {
	return ImageCheckboxConstraint{
		Type:    "imagecheckbox",
		Choices: choices,
	}
}

func NewSelectConstraint(choices []string) SelectConstraint {
	return SelectConstraint{
		Type:    "select",
		Choices: choices,
	}
}

func GetMainConfigConstraints() map[string]interface{} {
	portMin := 1024
	portMax := 65535

	// Combine them into a map for use in the config
	return map[string]interface{}{
		"ADB": map[string]interface{}{
			"Port": NewNumberConstraint(&portMin, &portMax, nil),
		},
		"Logging": map[string]interface{}{
			"Level": NewSelectConstraint([]string{
				string(LogLevelDebug),
				string(LogLevelInfo),
				string(LogLevelWarning),
				string(LogLevelError),
				string(LogLevelFatal),
			}),
		},
	}
}
