import posthog from "posthog-js";
import { getVersion } from "@tauri-apps/api/app";

const POSTHOG_KEY = "phc_GXmHn56fL10ymOt3inmqSER4wh5YuN3AG6lmauJ5b0o";
const POSTHOG_HOST = "https://eu.i.posthog.com";

export async function initPostHog() {
  if (posthog.__loaded) {
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
      app_version: await getVersion(),
    });
  } catch (error) {
    console.error(error);
  }
}
