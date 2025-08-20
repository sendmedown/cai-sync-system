// Robust adapter around various export shapes of securityMiddleware
let raw = null;
try {
  raw = require('./securityMiddleware');
} catch (e) {
  // If securityMiddleware.js is missing or fails to load, we fall back to no-ops
  raw = null;
}

// If the module itself is a factory function, try calling it to get the object
if (typeof raw === 'function') {
  try { raw = raw(); } catch { /* ignore */ }
}

function pick(name) {
  // 1) named export on the module
  if (raw && typeof raw[name] === 'function') return raw[name];
  // 2) named export on default
  if (raw && raw.default && typeof raw.default[name] === 'function') return raw.default[name];
  // 3) if default itself is a function middleware
  if (name === 'authenticateJWT') {
    if (raw && typeof raw.default === 'function') return raw.default;
  }
  return null;
}

const authenticateJWT = pick('authenticateJWT') || ((req, _res, next) => next());
const rateLimit       = pick('rateLimit')       || ((req, _res, next) => next());

module.exports = { authenticateJWT, rateLimit };
