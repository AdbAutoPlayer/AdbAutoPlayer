interface ConstraintSection {
  [key: string]: Constraint;
}

interface Constraints {
  [sectionKey: string]: ConstraintSection;
}

interface SettingsSection {
  [key: string]: any;
}

interface SettingsObject {
  [sectionKey: string]: SettingsSection;
}
