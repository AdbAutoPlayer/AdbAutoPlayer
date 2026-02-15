#!/usr/bin/env node

const { execSync } = require("child_process");
const process = require("process");
const path = require("path");
const { existsSync } = require("node:fs");

process.chdir(path.resolve(__dirname, ".."));

const extraArgs = process.argv.slice(2).join(" ");

function runCommand(cmd) {
  try {
    execSync(cmd, { stdio: "inherit" });
  } catch (err) {
    process.exit(1);
  }
}

function checkCommandExists(cmd, installHint) {
  try {
    execSync(`${cmd} --version`, { stdio: "ignore" });
    console.log(`Found '${cmd}'`);
  } catch (err) {
    console.error(`'${cmd}' is not installed.`);
    console.error(`Hint: ${installHint}`);
    process.exit(1);
  }
}

checkCommandExists("uv", "Install uv: https://github.com/astral-sh/uv");

const venvPath = path.join(process.cwd(), ".venv");

if (!existsSync(venvPath)) {
  runCommand("uv venv --python-preference only-system");
} else {
  console.log(".venv already exists, skipping...");
}

const isWin = process.platform === "win32";
const VENV_PATH = path.join(process.cwd(), ".venv");

function runInVenv(command) {
  let fullCmd;
  if (isWin) {
    // Windows: use cmd.exe /c to call the activate.bat
    const activate = path.join(VENV_PATH, "Scripts", "activate.bat");
    fullCmd = `cmd.exe /c "call ${activate} && ${command}"`;
  } else {
    // Unix/macOS: source the activate script in a shell
    const activate = path.join(VENV_PATH, "bin", "activate");
    fullCmd = `sh -c "source ${activate} && ${command}"`;
  }
  runCommand(fullCmd);
}

runInVenv("uv pip install --group dev -e src-tauri");
runCommand("pnpm install");
runInVenv(`pnpm tauri ${extraArgs}`);
