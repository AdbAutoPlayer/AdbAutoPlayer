interface MenuButton {
  label: string;
  callback: (...args: any[]) => void;
  active: boolean;
  alwaysEnabled?: boolean;
}

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
}

interface CheckboxConstraint extends BaseConstraint {
  type: "checkbox";
}

interface MultiCheckboxConstraint extends BaseConstraint {
  type: "multicheckbox";
  choices: string[];
}

interface ImageCheckboxConstraint extends BaseConstraint {
  type: "imagecheckbox";
  choices: string[];
}

interface SelectConstraint extends BaseConstraint {
  type: "select";
  choices: string[];
}

// Combined constraint type
type Constraint =
  | NumberConstraint
  | CheckboxConstraint
  | MultiCheckboxConstraint
  | ImageCheckboxConstraint
  | SelectConstraint
  | string[] // For arrays like "Order"
  | string; // For simple string values

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
