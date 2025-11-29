const fs = require("fs");
const path = require("path");

const newVersion = process.argv[2];

if (!newVersion) {
  console.error("❌ Usage: node set-version.js <version>");
  process.exit(1);
}

const configPath = path.join(__dirname, "src-tauri", "tauri.conf.json");

// Load file
const configRaw = fs.readFileSync(configPath, "utf8");
const config = JSON.parse(configRaw);

// Update version
config.version = newVersion;

// Save file back
fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + "\n");

console.log(`✅ Updated Tauri version to ${newVersion}`);
