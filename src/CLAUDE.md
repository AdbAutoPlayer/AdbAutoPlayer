# Frontend (SvelteKit + TypeScript)

- `src/lib/form/` — Dynamic JSON Schema form renderer; game settings are rendered entirely from Pydantic model schemas, not hardcoded components. A settings change usually needs no frontend edit — change the Pydantic model instead.
- `src/lib/stores.svelte.ts` — Global Svelte stores for app state (selected game, profile, running task, logs).
- `src/client/` — Auto-generated TypeScript client from PyTauri IPC definitions. **Never edit manually**; changes to Python IPC models regenerate it.
- SvelteKit is configured as a static SPA (no SSR); all routing is client-side for Tauri compatibility.
- Frontend listens for `log-message`, `task-completed` and `all-tasks-completed` events emitted from Python.

## SvelteKit 3 conventions

- **Imports**: use `#lib/...` and `#pytauri/...` (Node subpath imports declared in `package.json` `"imports"`), never `$lib` / `$pytauri` — SvelteKit 3 removed `$lib` and deprecated `alias`. Always write the **file extension**: `#lib/i18n/i18n.ts`, `#lib/stores.svelte.ts`, `#pytauri/_apiTypes.d.ts`, `#lib/form/SchemaForm.svelte`. Subpath imports never probe for extensions, so `#lib/i18n/i18n` fails to resolve.
- **Config**: there is no `svelte.config.js` (SvelteKit 3 refuses to start if it exists); adapter and preprocess options live in the `sveltekit({...})` plugin in `vite.config.ts`.
- **Global types**: `tsconfig.json` extends `$app/tsconfig`, which sets `moduleDetection: "force"` — a `.ts` file without imports/exports is a module, not a global script. Ambient types shared without imports (`LogMessage`, `IconProps`, …) must live in `.d.ts` files (`src/lib/types.d.ts`, `src/lib/types/*.d.ts`).
- **Hook types** moved to `@sveltejs/kit/hooks` (e.g. `HandleClientError`), and `handleError` receives `{ kind, error }` instead of `{ status, message }`.

Checks: `pnpm check` (svelte-check + TS) and `pnpm prettier-write` from the repo root.
