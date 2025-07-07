import posthog from "posthog-js";
import { browser } from "$app/environment";
import { version } from "$app/environment";

const POSTHOG_KEY = "phc_GXmHn56fL10ymOt3inmqSER4wh5YuN3AG6lmauJ5b0o";
const POSTHOG_HOST = "https://eu.i.posthog.com";

export function initPostHog() {
  if (!browser) {
    return;
  }

  try {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      autocapture: {
        css_selector_allowlist: [".ph-autocapture"],
      },
      person_profiles: "always",
    });

    posthog.register({
      app_version: version as string,
    });
  } catch (error) {
    console.error("Failed to initialize PostHog:", error);
  }
}
