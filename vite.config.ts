import adapter from "@sveltejs/adapter-static";
import { sveltekit } from "@sveltejs/kit/vite";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import devtoolsJson from "vite-plugin-devtools-json";

export default defineConfig({
  plugins: [
    tailwindcss(),
    // SvelteKit 3 takes its config here instead of svelte.config.js.
    // Tauri doesn't have a Node.js server to do proper SSR, so we use
    // adapter-static with a fallback to index.html to put the site in SPA mode
    // See: https://svelte.dev/docs/kit/single-page-apps
    // See: https://v2.tauri.app/start/frontend/sveltekit/ for more info
    sveltekit({
      preprocess: vitePreprocess(),
      adapter: adapter({
        // match `build.frontendDist` in `tauri.conf.json`
        pages: "dist",
        fallback: "index.html",
      }),
      // `#lib/...` and `#pytauri/...` imports are Node subpath imports,
      // declared in package.json "imports" (SvelteKit 3 dropped `$lib`)
    }),
    devtoolsJson(),
  ],
  optimizeDeps: {
    exclude: ["@skeletonlabs/skeleton-svelte", "@skeletonlabs/skeleton"],
  },

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    host: "127.0.0.1",
    port: 1420,
    strictPort: true,
    watch: {
      // 3. tell vite to ignore watching `src-tauri`
      ignored: [
        "**/src-tauri/**",
        "**/.venv/**",
        "**/data/**",
        "**/debug/**",
        "**/ocr_debug.txt",
        "**/full_hero_report.txt",
        "**/hero_audit_report.txt",
      ],
    },
  },
});
