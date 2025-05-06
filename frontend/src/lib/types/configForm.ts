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
