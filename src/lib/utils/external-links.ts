// @ts-ignore
import { showErrorToast } from "$lib/toast/toast-error";
import { openUrl } from "@tauri-apps/plugin-opener";

export function shouldOpenExternally(url: string): boolean {
  if (!url) {
    return false;
  }
  if (url.startsWith("#") || url.startsWith("/")) {
    return false;
  }

  try {
    const parsedUrl = new URL(url);
    if (parsedUrl.host === "wails.localhost") {
      return false;
    }
  } catch {
    return false;
  }

  if (url.startsWith("file://")) {
    return false;
  }

  return url.includes("://");
}

export function setupExternalLinkHandler(): () => void {
  const handleClick = (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    const anchor = target.closest("a");

    if (!(anchor instanceof HTMLAnchorElement)) {
      return;
    }

    const url = anchor.href;

    if (shouldOpenExternally(url)) {
      e.preventDefault();
      openUrl(url).catch((e: any) => {
        void showErrorToast(e);
      });
    }
  };

  document.body.addEventListener("click", handleClick);

  return () => {
    document.body.removeEventListener("click", handleClick);
  };
}
