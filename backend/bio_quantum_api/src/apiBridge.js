// Minimal API Bridge (clean)
// Public: /health, /auth/token
// Protected (JWT): /metrics
require('dotenv').config();

const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');

const app = express();
const PORT = parseInt(process.env.PORT || '10000', 10);
const JWT_SECRET = process.env.JWT_SECRET || 'dev_dummy_123';

app.use(cors());
app.use(express.json());

// Public endpoints (no auth)
app.get('/health', (req, res) => res.status(200).json({ status: 'ready' }));

app.post('/auth/token', (req, res) => {
  const { userId = 'dev', role = 'user' } = req.body || {};
  const token = jwt.sign({ sub: userId, role }, JWT_SECRET, { expiresIn: '1h' });
  res.json({ token });
});

// Load security middleware if present; fall back to no-ops
let securityMiddleware;
try {
  const sm = require('../middleware/securityMiddleware');
  securityMiddleware = sm && (sm.default || sm);
} catch (_) {
  securityMiddleware = null;
}

const authMw       = securityMiddleware?.authenticateJWT || securityMiddleware?.auth || ((req,res,next)=>next());
const rateLimitMw  = securityMiddleware?.rateLimit       || ((req,res,next)=>next());

// Skip auth/rate limit for the public paths
const PUBLIC_PATHS = new Set(['/health', '/auth/token']);
app.use((req,res,next) => PUBLIC_PATHS.has(req.path) ? next() : authMw(req,res,next));
app.use((req,res,next) => PUBLIC_PATHS.has(req.path) ? next() : rateLimitMw(req,res,next));

// Example protected route (requires Authorization: Bearer <token>)
app.get('/metrics', (req, res) => {
  res.json({ ok: true, ts: Date.now() });
});

app.listen(PORT, () => {
  console.log(`🚀 API Bridge server listening on ${PORT}`);
});
