import fs from "fs-extra";
import path from "path";

async function moveBuildDir() {
  const buildDir = path.resolve("build");
  const targetDir = path.resolve("..", "cmd", "wails", "frontend", "build");

  try {
    await fs.ensureDir(targetDir);

    await fs.copy(buildDir, targetDir, { overwrite: true });
    console.log("Build directory moved successfully!");
  } catch (error) {
    console.error("Error moving build directory:", error);
  }
}

await moveBuildDir();
