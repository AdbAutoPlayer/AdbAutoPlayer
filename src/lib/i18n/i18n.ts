import { derived, type Readable, writable } from "svelte/store";
import locales, { SupportedLocale } from "./locales";

type InterpolationValues = Record<string, string>;

export const appLocale = writable<SupportedLocale>(SupportedLocale.EN);

type TranslationFunction = (
  text: string,
  values?: InterpolationValues,
) => string;

// Translation function
export const t: Readable<TranslationFunction> = derived(
  [appLocale],
  ([$locale]) => {
    return (text: string, values: InterpolationValues = {}) => {
      return translate(text, $locale, values);
    };
  },
);

export function translate(
  text: string,
  locale: SupportedLocale = SupportedLocale.EN,
  values: InterpolationValues = {},
): string {
  if (locale !== SupportedLocale.EN) {
    const trans = locales[locale]?.[text];
    if (trans) {
      text = trans;
    }
  }

  return Object.keys(values).length === 0
    ? text
    : text.replace(/\{\{(\w+)}}/g, (_, key) => values[key] || "");
}
