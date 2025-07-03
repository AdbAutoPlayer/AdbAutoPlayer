// import json here
import jp from "./jp.json";

// Add Locale here
export enum SupportedLocale {
  EN = "en",
  JP = "jp",
}

type Translations = Record<string, string>;
type LocaleDictionary = Record<SupportedLocale, Translations>;

const locales: LocaleDictionary = {
  [SupportedLocale.EN]: {}, // English uses default keys
  [SupportedLocale.JP]: jp,
};

export default locales;
export type { Translations, LocaleDictionary };
