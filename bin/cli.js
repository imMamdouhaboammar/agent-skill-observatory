#!/usr/bin/env node
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import fs from "node:fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..");
const venvSkillobs = resolve(repoRoot, ".venv", "bin", "skillobs");

let cmd = "skillobs";
let args = process.argv.slice(2);

if (fs.existsSync(venvSkillobs)) {
  cmd = venvSkillobs;
} else {
  // Fallback to python module execution if skillobs binary isn't in global PATH
  cmd = "python3";
  args = ["-m", "skill_observatory", ...process.argv.slice(2)];
}

const child = spawn(cmd, args, { stdio: "inherit", cwd: process.cwd() });
child.on("exit", (code) => {
  process.exit(code ?? 0);
});
