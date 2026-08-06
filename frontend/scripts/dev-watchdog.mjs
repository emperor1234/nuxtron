import http from 'node:http';
import { spawn } from 'node:child_process';
import { access } from 'node:fs/promises';
import path from 'node:path';

const WATCHDOG_TAG = '[dev-watchdog]';
const FRONTEND_URL = 'http://127.0.0.1:4173/';
const HEALTH_CHECK_INTERVAL_MS = 5000;
const HEALTH_CHECK_TIMEOUT_MS = 1500;
const RESTART_DELAY_MS = 1500;
const HEALTH_FAILURE_THRESHOLD = 3;

let child = null;
let stopping = false;
let healthTimer = null;
let installPromise = null;
let consecutiveHealthFailures = 0;

function log(message) {
  console.log(`${WATCHDOG_TAG} ${message}`);
}

async function pathExists(targetPath) {
  try {
    await access(targetPath);
    return true;
  } catch {
    return false;
  }
}

function runNpmInstall() {
  return new Promise((resolve) => {
    const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
    log('Missing frontend runtime dependencies. Running npm install...');

    const installChild = spawn(npmCommand, ['install'], {
      stdio: 'inherit',
      env: process.env,
      cwd: process.cwd(),
      shell: process.platform === 'win32',
    });

    installChild.on('error', (error) => {
      log(`npm install failed to start: ${error.message}`);
      resolve(false);
    });

    installChild.on('exit', (code) => {
      if (code === 0) {
        log('npm install completed successfully.');
        resolve(true);
        return;
      }

      log(`npm install exited with code ${code ?? 'null'}.`);
      resolve(false);
    });
  });
}

async function ensureRuntimeDependencies() {
  if (installPromise) {
    return installPromise;
  }

  const required = [
    path.join(process.cwd(), 'node_modules', 'next', 'package.json'),
    path.join(process.cwd(), 'node_modules', '@swc', 'helpers', 'package.json'),
  ];

  const missing = [];
  for (const requiredPath of required) {
    // Keep checks explicit so missing core packages fail fast before boot loops.
    if (!(await pathExists(requiredPath))) {
      missing.push(requiredPath);
    }
  }

  if (missing.length === 0) {
    return true;
  }

  log(`Dependency check failed. Missing: ${missing.join(', ')}`);
  installPromise = runNpmInstall();
  const installed = await installPromise;
  installPromise = null;
  if (!installed) {
    return false;
  }

  for (const requiredPath of required) {
    if (!(await pathExists(requiredPath))) {
      log(`Dependency check still failing after install: ${requiredPath}`);
      return false;
    }
  }

  return true;
}

function checkFrontendHealth() {
  return new Promise((resolve) => {
    const request = http.get(FRONTEND_URL, (response) => {
      response.resume();
      resolve(response.statusCode !== undefined && response.statusCode < 500);
    });

    request.setTimeout(HEALTH_CHECK_TIMEOUT_MS, () => {
      request.destroy(new Error('Health check timed out'));
    });

    request.on('error', () => resolve(false));
  });
}

function spawnDevServer() {
  const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  log('Starting frontend dev server on port 4173...');

  child = spawn(npmCommand, ['run', 'dev'], {
    stdio: 'inherit',
    env: process.env,
    cwd: process.cwd(),
    shell: process.platform === 'win32',
  });

  child.on('error', (error) => {
    child = null;
    if (stopping) return;
    log(`Failed to spawn dev server: ${error.message}. Retrying in ${RESTART_DELAY_MS}ms...`);
    setTimeout(() => {
      void ensureFrontendIsRunning();
    }, RESTART_DELAY_MS);
  });

  child.on('exit', (code, signal) => {
    child = null;
    if (stopping) return;
    log(
      `Dev server exited (code=${code ?? 'null'}, signal=${signal ?? 'none'}). Restarting in ${RESTART_DELAY_MS}ms...`
    );
    setTimeout(() => {
      void ensureFrontendIsRunning();
    }, RESTART_DELAY_MS);
  });
}

async function ensureFrontendIsRunning() {
  if (stopping || child) return;

  const dependenciesReady = await ensureRuntimeDependencies();
  if (!dependenciesReady) {
    log(`Dependencies are still missing. Retrying in ${RESTART_DELAY_MS}ms...`);
    setTimeout(() => {
      void ensureFrontendIsRunning();
    }, RESTART_DELAY_MS);
    return;
  }

  const healthy = await checkFrontendHealth();
  if (healthy) {
    consecutiveHealthFailures = 0;
    log('Port 4173 is already healthy. Monitoring and waiting for changes...');
    return;
  }

  spawnDevServer();
}

function startHealthMonitor() {
  if (healthTimer) return;

  healthTimer = setInterval(() => {
    if (stopping || child) return;

    void checkFrontendHealth().then((healthy) => {
      if (healthy) {
        consecutiveHealthFailures = 0;
        return;
      }

      consecutiveHealthFailures += 1;
      if (consecutiveHealthFailures >= HEALTH_FAILURE_THRESHOLD) {
        consecutiveHealthFailures = 0;
        log('Frontend is down. Attempting restart...');
        void ensureFrontendIsRunning();
      }
    });
  }, HEALTH_CHECK_INTERVAL_MS);
}

function stopWatchdog(signal) {
  if (stopping) return;
  stopping = true;

  if (healthTimer) {
    clearInterval(healthTimer);
    healthTimer = null;
  }

  log(`Received ${signal}. Stopping watchdog...`);

  if (child) {
    child.kill('SIGINT');
  }
}

process.on('SIGINT', () => stopWatchdog('SIGINT'));
process.on('SIGTERM', () => stopWatchdog('SIGTERM'));

log('Booting watchdog...');
startHealthMonitor();
await ensureFrontendIsRunning();
