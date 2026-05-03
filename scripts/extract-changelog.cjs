const fs = require("fs");
const path = require("path");

const version = process.argv[2];
if (!version) {
  console.error("Usage: node extract-changelog.cjs <version>");
  process.exit(1);
}

const changelogPath = path.join(__dirname, "..", "CHANGELOG.md");
if (!fs.existsSync(changelogPath)) {
  console.error("CHANGELOG.md not found");
  process.exit(1);
}

const content = fs.readFileSync(changelogPath, "utf8");
const lines = content.split("\n");

let capturing = false;
let notes = [];

// Clean version string (remove 'v' prefix if present)
const targetVersion = version.startsWith("v") ? version.substring(1) : version;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];

  // Check for version header: ## [1.2.3] or ## 1.2.3
  const versionHeaderMatch = line.match(/^##\s+\[?([\d.]+)\]?/);

  if (versionHeaderMatch) {
    const foundVersion = versionHeaderMatch[1];
    if (foundVersion === targetVersion) {
      capturing = true;
      continue;
    } else if (capturing) {
      // Hit the next version header, stop
      break;
    }
  }

  if (capturing) {
    notes.push(line);
  }
}

const result = notes.join("\n").trim();
if (result) {
  console.log(result);
} else {
  console.error(`No notes found for version ${targetVersion}`);
  process.exit(1);
}
