// import json here
import jp from "./jp.json";
import vn from "./vn.json";

// Add Locale here
export enum SupportedLocale {
  EN = "en",
  JP = "jp",
  VN = "vn",
}

type Translations = Record<string, string>;
type LocaleDictionary = Record<SupportedLocale, Translations>;

const locales: LocaleDictionary = {
  [SupportedLocale.EN]: {}, // English uses default keys
  [SupportedLocale.JP]: jp,
  [SupportedLocale.VN]: vn,
};

export default locales;
export type { Translations, LocaleDictionary };
