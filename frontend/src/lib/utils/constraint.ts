export function isConstraintOfType<T extends keyof ConstraintTypeMap>(
  value: any,
  type: T,
): value is ConstraintTypeMap[T] {
  return typeof value === "object" && value !== null && value.type === type;
}
