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

interface MyCustomRoutineConstraint extends BaseConstraint {
  type: "MyCustomRoutine";
  choices: string[];
  default_value: string[];
}

interface TextConstraint extends BaseConstraint {
  type: "text";
  regex: string;
  title: string;
  default_value: string;
}

type ConstraintTypeMap = {
  number: NumberConstraint;
  checkbox: CheckboxConstraint;
  multicheckbox: MultiCheckboxConstraint;
  imagecheckbox: ImageCheckboxConstraint;
  select: SelectConstraint;
  text: TextConstraint;
  MyCustomRoutine: MyCustomRoutineConstraint;
};

type Constraint = ConstraintTypeMap[keyof ConstraintTypeMap] | string[];
