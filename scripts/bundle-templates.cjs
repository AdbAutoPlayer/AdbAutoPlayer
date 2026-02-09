const fs = require("fs");
const path = require("path");

const GAMES_DIR = path.join(
  __dirname,
  "../src-tauri/src-python/adb_auto_player/games",
);
const OUTPUT_FILE = path.join(
  __dirname,
  "../src-tauri",
  "tauri.bundle.templates.json",
);

// Helper to check if a directory exists
const isDir = (source) =>
  fs.existsSync(source) && fs.lstatSync(source).isDirectory();

// Scan all games
const games = fs.readdirSync(GAMES_DIR).filter((game) => {
  const gamePath = path.join(GAMES_DIR, game);
  return isDir(gamePath);
});

// Build resources object
const resources = {};
games.forEach((game) => {
  const templatePath = path.join(GAMES_DIR, game, "templates");
  if (isDir(templatePath)) {
    const relativeSrc = `src-python/adb_auto_player/games/${game}/templates/`;
    const relativeDest = `./games/${game}/templates/`;
    resources[relativeSrc] = relativeDest;
  }
});

// Create JSON structure
const bundleJson = {
  bundle: {
    resources,
  },
};

// Write to file
fs.writeFileSync(OUTPUT_FILE, JSON.stringify(bundleJson, null, 2) + "\n");
console.log(`✅ Generated Tauri bundle templates at ${OUTPUT_FILE}`);
