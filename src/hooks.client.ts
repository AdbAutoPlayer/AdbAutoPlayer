import posthog from "posthog-js";
import type { HandleClientError } from "@sveltejs/kit";

export const handleError: HandleClientError = async ({
  error,
  event,
  status,
  message,
}) => {
  if (error && status !== 404) {
    posthog.captureException(error);
  }
};
