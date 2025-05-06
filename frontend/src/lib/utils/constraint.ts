export function isArrayInputConstraint(constraint: Constraint): boolean {
  return (
    typeof constraint === "object" &&
    constraint !== null &&
    Array.isArray((constraint as any).default_value)
  );
}

export function isConstraintOfType<T extends keyof ConstraintTypeMap>(
  value: any,
  type: T,
): value is ConstraintTypeMap[T] {
  return typeof value === "object" && value !== null && value.type === type;
}
