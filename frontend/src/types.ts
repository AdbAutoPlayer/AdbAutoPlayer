type LogLevel = "TRACE" | "DEBUG" | "INFO" | "WARNING" | "ERROR" | "FATAL";

interface LogMessage {
  level: LogLevel;
  message: string;
  timestamp: string;
  source_file?: string;
  function_name?: string;
  line_number?: number;
}

interface BaseConstraint {
  type: string;
}

interface NumberConstraint extends BaseConstraint {
  type: "number";
  step: number;
  minimum: number;
  maximum: number;
  default_value: number;
}

interface CheckboxConstraint extends BaseConstraint {
  type: "checkbox";
  default_value: boolean;
}

interface MultiCheckboxConstraint extends BaseConstraint {
  type: "multicheckbox";
  choices: string[];
  default_value: string[];
  group_alphabetically: boolean;
}

interface ImageCheckboxConstraint extends BaseConstraint {
  type: "imagecheckbox";
  choices: string[];
  default_value: string[];
  image_dir_path: string;
}

interface SelectConstraint extends BaseConstraint {
  type: "select";
  choices: string[];
  default_value: string;
}

interface TextConstraint extends BaseConstraint {
  type: "text";
  regex: string;
  title: string;
  default_value: string;
}

// Combined constraint type
type Constraint =
  | NumberConstraint
  | CheckboxConstraint
  | MultiCheckboxConstraint
  | ImageCheckboxConstraint
  | SelectConstraint
  | TextConstraint
  | string[]; // For arrays like "Order"

interface ConstraintSection {
  [key: string]: Constraint;
}

interface Constraints {
  [sectionKey: string]: ConstraintSection;
}

interface ConfigSection {
  [key: string]: any;
}

interface ConfigObject {
  [sectionKey: string]: ConfigSection;
}
