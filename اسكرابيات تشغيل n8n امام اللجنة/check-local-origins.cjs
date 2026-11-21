// Read-only development preflight. Do not print environment values or secrets.
const path = require('node:path');
const frontend = path.resolve(__dirname, '../frontend');
require(path.join(frontend, 'node_modules/@next/env')).loadEnvConfig(frontend, true);
const errors = [];
function checkOrigin(key, expectedPort) {
  const value = process.env[key]?.trim();
  if (!value) return;
  try {
    const url = new URL(value);
    if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname)
      || url.port !== String(expectedPort) || url.username || url.password
      || url.search || url.hash || url.pathname.replace(/\/+$/, '')) throw new Error();
  } catch { errors.push(key + ' must target the documented local port ' + expectedPort); }
}
checkOrigin('INTERNAL_API_URL', 8000);
checkOrigin('NEXT_PUBLIC_API_BASE_URL', 8000);
checkOrigin('NEXT_PUBLIC_SITE_URL', 3001);
const pkg = require(path.join(frontend, 'package.json'));
if (pkg.scripts.dev !== 'next dev --port 3001' || pkg.scripts.start !== 'next start --port 3001') {
  errors.push('Frontend package scripts must explicitly use port 3001');
}
console.log(JSON.stringify({ok: errors.length === 0, errors}));
process.exitCode = errors.length ? 1 : 0;
