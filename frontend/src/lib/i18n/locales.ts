// import json here
import jpGeneral from "./jp_general.json";
import jpAFKJourney from "./jp_afk_journey.json";
import jpAFKJourneyHeroes from "./jp_afk_journey_heroes.json";
import vn from "./vn.json";

// Add Locale here
export enum SupportedLocale {
  EN = "en",
  JP = "jp",
  VN = "vn",
}

const locales: LocaleDictionary = {
  [SupportedLocale.EN]: {}, // English uses default keys
  [SupportedLocale.JP]: mergeTranslations(
    [jpGeneral, jpAFKJourneyHeroes, jpAFKJourney],
    SupportedLocale.JP,
  ),
  [SupportedLocale.VN]: vn,
};

type Translations = Record<string, string>;
type LocaleDictionary = Record<SupportedLocale, Translations>;
export default locales;
export type { Translations, LocaleDictionary };

/**
 * Merges multiple translation objects, throwing an error if duplicate keys are found
 * @param sources - Array of translation objects to merge
 * @param locale - The locale being processed (for error messages)
 * @returns Merged translations object
 */
function mergeTranslations(
  sources: Translations[],
  locale: string,
): Translations {
  const merged: Translations = {};
  const seenKeys = new Set<string>();

  for (const source of sources) {
    for (const [key, value] of Object.entries(source)) {
      if (seenKeys.has(key)) {
        throw new Error(
          `Duplicate translation key "${key}" found in locale "${locale}". ` +
            `Please ensure all keys are unique across all files for this locale.`,
        );
      }
      seenKeys.add(key);
      merged[key] = value;
    }
  }

  return merged;
}
