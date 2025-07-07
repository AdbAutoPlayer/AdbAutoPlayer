import { writable, derived, type Readable } from "svelte/store";
import locales, { SupportedLocale } from "./locales";

type InterpolationValues = Record<string, string>;

export const locale = writable<SupportedLocale>(SupportedLocale.EN);
export const translations = writable(locales);

type TranslationFunction = (
  text: string,
  values?: InterpolationValues,
) => string;

// Translation function
export const t: Readable<TranslationFunction> = derived(
  [locale, translations],
  ([$locale, $translations]) => {
    return (text: string, values: InterpolationValues = {}) => {
      if ($locale === SupportedLocale.EN) {
        return interpolate(text, values);
      }

      const translation = $translations[$locale]?.[text];
      return interpolate(translation || text, values);
    };
  },
);

function interpolate(text: string, values: InterpolationValues): string {
  return Object.keys(values).length === 0
    ? text
    : text.replace(/\{\{(\w+)}}/g, (_, key) => values[key] || "");
}

export function setLocale(newLocale: string): void {
  if (Object.values(SupportedLocale).includes(newLocale as SupportedLocale)) {
    locale.set(newLocale as SupportedLocale);
  } else {
    console.warn(
      `Locale "${newLocale}" is not supported. Falling back to "${SupportedLocale.EN}".`,
    );
    locale.set(SupportedLocale.EN);
  }
}
