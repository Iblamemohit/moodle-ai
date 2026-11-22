#!/usr/bin/env node
/**
 * moodle-ai CLI launcher.
 * Forwards arguments to the local virtual environment Python runner without global cache overhead.
 */
const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';
const venvPy = path.join(rootDir, '.venv', isWin ? 'Scripts/python.exe' : 'bin/python');
const pyBin = fs.existsSync(venvPy) ? venvPy : (isWin ? 'python' : 'python3');
const moodleScript = path.join(rootDir, 'moodle.py');

const args = process.argv.slice(2);
const result = spawnSync(pyBin, [moodleScript, ...args], {
  cwd: rootDir,
  stdio: 'inherit',
  env: process.env
});

process.exit(result.status ?? 0);
