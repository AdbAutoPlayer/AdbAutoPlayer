import type { JSONSchema } from "json-schema-to-typescript";

export interface ArraySchema {
  type: "array";
  items: JSONSchema;
  formType?: string;
  assetPath?: string;
  title?: string;
  default?: any[];
  minItems?: number;
}

export function asArraySchema(prop: any): ArraySchema | null {
  if (prop.type === "array" && prop.items) {
    return prop as ArraySchema;
  }
  return null;
}

interface StringChoiceValueArrayProps {
  choices: NonEmptyArray<string>;
  value: string[];
}

export type TaskListProps = StringChoiceValueArrayProps;
export type CheckboxArrayProps = StringChoiceValueArrayProps;

export interface AlnumGroupedCheckboxArrayProps extends StringChoiceValueArrayProps {
  title: string;
}

export interface ImageCheckboxArrayProps extends StringChoiceValueArrayProps {
  assetPath: string;
}

export interface StringValueArrayProps {
  value: string[];
  minItems?: number;
}

export function asNonEmptyStringArray(
  schema: any,
): NonEmptyArray<string> | null {
  const arraySchema = asArraySchema(schema);

  if (!arraySchema) {
    return null;
  }

  const choices = arraySchema.items.enum;

  if (!isStringArray(choices) || choices.length === 0) {
    return null;
  }

  return choices as NonEmptyArray<string>;
}

const isStringArray = (arr: any): arr is string[] =>
  Array.isArray(arr) && arr.every((i) => typeof i === "string");
