import posthog from "posthog-js";
import type { HandleClientError } from "@sveltejs/kit/hooks";

const NOT_FOUND = 404;

export const handleError: HandleClientError = async ({ kind, error }) => {
  // A 404 is a SvelteKit framework error (unknown route), not a bug to report
  if (kind === "framework" && error.status === NOT_FOUND) {
    return;
  }
  if (error) {
    posthog.captureException(error);
  }
};
