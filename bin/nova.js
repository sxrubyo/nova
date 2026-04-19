#!/usr/bin/env node

const { spawnSync } = require('node:child_process');
const { join } = require('node:path');

const repoDir = join(__dirname, '..');
const bootstrapPath = join(repoDir, 'nova', 'bootstrap.py');

function resolvePython() {
  const candidates = [
    ['python3'],
    ['python'],
    ['py', '-3'],
  ];

  for (const candidate of candidates) {
    const probe = spawnSync(candidate[0], [...candidate.slice(1), '--version'], {
      stdio: 'ignore',
    });
    if (probe.status === 0) {
      return candidate;
    }
  }

  console.error('Nova requires Python 3 on the host. Install python3 and retry.');
  process.exit(1);
}

const python = resolvePython();
const result = spawnSync(
  python[0],
  [
    ...python.slice(1),
    bootstrapPath,
    'exec',
    '--repo',
    repoDir,
    '--',
    ...process.argv.slice(2),
  ],
  { stdio: 'inherit' },
);

if (typeof result.status === 'number') {
  process.exit(result.status);
}

process.exit(1);
