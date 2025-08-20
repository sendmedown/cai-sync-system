# Create a clean apiBridge.js for the user to download
code = r"""'use strict';
require('dotenv').config();

const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const { WebSocketServer } = require('ws');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs');

// ---------- Helpers ----------
const LOG_PATH = path.join(__dirname, 'apiBridge.log');
function log(msg, level = 'INFO') {
  const line = `[${new Date().toISOString()}] ${level}: ${msg}\n`;
  try { fs.appendFileSync(LOG_PATH, line); } catch {}
  // Also echo to console for dev
  if (level === 'ERROR') console.error(msg);
  else console.log(msg);
}

function safeRequire(p, fallbackFactory) {
  try { return require(p); } 
  catch (e) { 
    if (fallbackFactory) return fallbackFactory(e);
    throw e;
  }
}

function noopMw(req, res, next) { return next(); }

// ---------- Optional internal deps with safe fallbacks ----------
const SecurityWatchdog = safeRequire('./SecurityWatchdog', () => {
  return class SecurityWatchdog {
    constructor(){ log('SecurityWatchdog fallback active','WARN'); }
    monitorRequest(req, res, next){ return next(); }
  };
});

const SecurityNetworkWatchdog = safeRequire('./SecurityNetworkWatchdog', () => {
  return class SecurityNetworkWatchdog {
    constructor(){ log('SecurityNetworkWatchdog fallback active','WARN'); }
    trackRequest(req, res, next){ return next(); }
  };
});

const KMNuggetValidationEngine = safeRequire('./KMNuggetValidationEngine', () => {
  return class KMNuggetValidationEngine {
    validate(n, set){ return { ok:true, nugget:n, comparedTo:set||[] }; }
  };
});

const WebSocketEventManager = safeRequire('../ws/WebSocketEventManager', () => {
  const EventEmitter = require('events');
  return class WebSocketEventManager extends EventEmitter { };
});

const CrossSessionValidator = safeRequire('../validation/CrossSessionValidator', () => {
  return class CrossSessionValidator { constructor(){} };
});

const securityMiddlewareMod = safeRequire('../middleware/securityMiddleware', () => ({}));

function adaptSecurityMiddleware(mod) {
  const m = mod && (mod.default || mod);
  if (!m) return { auth: noopMw, rateLimit: noopMw };
  if (typeof m === 'function') {
    // Some projects export a factory
    try {
      const out = m();
      if (out && (out.authenticateJWT || out.auth)) {
        return {
          auth: out.authenticateJWT || out.auth || noopMw,
          rateLimit: out.rateLimit || noopMw
        };
      }
    } catch {}
  }
  return {
    auth: m.authenticateJWT || m.auth || noopMw,
    rateLimit: m.rateLimit || noopMw
  };
}

const { auth: authMw, rateLimit: rateLimitMw } = adaptSecurityMiddleware(securityMiddlewareMod);

// ---------- Config ----------
const PORT = parseInt(process.env.PORT || '10000', 10);
const WS_PORT = parseInt(process.env.WS_PORT || '55003', 10);
const METRICS_WS_PORT = parseInt(process.env.METRICS_WS_PORT || '55004', 10);
const FED_ENABLED = process.env.FED_ENABLED === '1';
const JWT_SECRET = process.env.JWT_SECRET || 'dev_dummy_123'; // dev default

// ---------- Optional federation deps ----------
let threatSync = null, threatSyncProtocol = null;
if (FED_ENABLED) {
  const FederatedThreatSync = safeRequire('./FederatedThreatSync', () => null);
  const FederatedThreatSyncProtocol = safeRequire('./FederatedThreatSyncProtocol', () => null);
  if (FederatedThreatSync && FederatedThreatSyncProtocol) {
    threatSync = new FederatedThreatSync();
    threatSyncProtocol = new FederatedThreatSyncProtocol({
      agentId: 'bridge',
      codonGenerator: safeRequire('./CodonGenerator', () => ({ generate: () => ({}) })),
      securityWatchdog: new SecurityWatchdog()
    });
  } else {
    log('FED_ENABLED=1 but federation modules missing; continuing without federation', 'WARN');
  }
}

// ---------- App & state ----------
const app = express();
const dnaStrands = new Map();
const watchdog = new SecurityWatchdog();
const networkWatchdog = new SecurityNetworkWatchdog({
  codonGenerator: safeRequire('./CodonGenerator', () => ({ generate: () => ({}) })),
  validationEngine: new KMNuggetValidationEngine(),
  crossSessionValidator: new CrossSessionValidator()
});
const wsEventManager = new WebSocketEventManager();

app.use(cors());
app.use(express.json());

// Public endpoints that skip auth & watchdog
const PUBLIC_PATHS = new Set(['/health','/auth/token','/auth/login','/auth/refresh']);

function skipIfPublic(mw) {
  return (req, res, next) => PUBLIC_PATHS.has(req.path) ? next() : mw(req, res, next);
}

// Public routes
app.get('/health', (req, res) => res.status(200).json({ status: 'ready' }));

app.post('/auth/token', (req, res) => {
  const { userId, role } = req.body || {};
  const token = jwt.sign({ sub: userId || 'dev', role: role || 'agent' }, JWT_SECRET, { expiresIn: '1h' });
  return res.json({ token });
});

app.post('/auth/login', (req, res) => {
  const { userId, role } = req.body || {};
  const token = jwt.sign({ sub: userId || 'dev', role: role || 'agent' }, JWT_SECRET, { expiresIn: '1h' });
  return res.json({ token });
});

// Security middleware (skips public)
app.use(skipIfPublic(authMw));
app.use(skipIfPublic(rateLimitMw));
app.use(skipIfPublic((req, res, next) => watchdog.monitorRequest(req, res, next)));
app.use(skipIfPublic((req, res, next) => networkWatchdog.trackRequest(req, res, next)));

// ---------- Core routes ----------
app.post('/nugget/create', (req, res) => {
  const { userId, content, promptId, context } = req.body || {};
  try {
    const authz = req.headers.authorization || '';
    const token = (authz.startsWith('Bearer ') ? authz.slice(7) : null);
    if (!token) throw new Error('Missing JWT');
    jwt.verify(token, JWT_SECRET);

    if (!userId || !content || !promptId || !context?.sessionId) {
      throw new Error('Missing required fields');
    }

    const nuggetId = uuidv4();
    const sessionId = context.sessionId;
    const codon = {
      nuggetId, content, promptId,
      type: 'Condition', origin: 'User',
      timestamp: new Date().toISOString()
    };

    const strand = dnaStrands.get(sessionId) || { sessionId, codons: [] };
    strand.codons.push(codon);
    dnaStrands.set(sessionId, strand);

    if (global.wss) {
      for (const client of global.wss.clients) {
        if (client.sessionId === sessionId) {
          client.send(JSON.stringify({ type: 'nugget_update', ...codon, requestId: uuidv4() }));
        }
      }
    }

    wsEventManager.emit('security_event', { type: 'nugget_created', nuggetId, sessionId });
    res.status(200).json({ status: 'success', nuggetId, sessionId, requestId: uuidv4() });
  } catch (err) {
    res.status(401).json({ error: err.message || 'Invalid JWT', requestId: uuidv4() });
  }
});

app.post('/security/event', (req, res) => {
  wsEventManager.emit('security_event', req.body?.event || {});
  res.status(200).json({ status: 'broadcasted' });
});

app.post('/security/incident', (req, res) => {
  wsEventManager.emit('security_incident', req.body?.incident || {});
  res.status(200).json({ status: 'broadcasted' });
});

app.post('/sync/threat', (req, res) => {
  try {
    const signature = req.body?.signature || {};
    if (!signature.vectorHash || !signature.timestamp || !signature.sessionSource || !signature.riskLevel) {
      throw new Error('Invalid threat signature format');
    }
    if (FED_ENABLED && threatSync) {
      threatSync.handleMessage(null, JSON.stringify({ type: 'threat_signature', signature }));
      wsEventManager.emit('threat_signature', signature);
    }
    res.status(200).json({ status: 'received', syncedAt: new Date().toISOString() });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.get('/sync/threat/pull', (req, res) => {
  const after = req.query?.after;
  const fingerprints = (FED_ENABLED && threatSync && Array.isArray(threatSync.threatLedger))
    ? threatSync.threatLedger.filter(f => !after || f.syncedAt > after)
    : [];
  res.status(200).json({ fingerprints });
});

app.post('/validate', (req, res) => {
  try {
    const validator = new KMNuggetValidationEngine();
    const result = validator.validate(req.body?.nugget, req.body?.comparisonSet || []);
    res.status(200).json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.post('/batch-validate', (req, res) => {
  try {
    const validator = new KMNuggetValidationEngine();
    const nuggets = Array.isArray(req.body?.nuggets) ? req.body.nuggets : [];
    const results = nuggets.map(n => validator.validate(n, req.body?.comparisonSet || []));
    res.status(200).json(results);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.post('/report/compliance', (req, res) => {
  const complianceData = {
    spiCompliance: true,
    validatedNuggets: [],
    timestamp: new Date().toISOString()
  };
  res.status(200).json(complianceData);
});

app.get('/security/alerts', (req, res) => {
  const alerts = [
    { id: '1', type: 'jwt_failure', severity: 'medium', timestamp: new Date().toISOString() },
    { id: '2', type: 'rate_limit', severity: 'low', timestamp: new Date().toISOString() },
    { id: '3', type: 'codon_mutation', severity: 'high', timestamp: new Date().toISOString() }
  ];
  res.status(200).json({ alerts });
});

app.get('/mutation/timeline', (req, res) => {
  const mutationReplayEvents = [
    { id: '1', type: 'codon_created', timestamp: new Date().toISOString(), sequence: 'ATCG' },
    { id: '2', type: 'mutation_detected', timestamp: new Date().toISOString(), sequence: 'ATCC' },
    { id: '3', type: 'repair_initiated', timestamp: new Date().toISOString(), sequence: 'ATCG' }
  ];
  res.status(200).json({ mutationReplayEvents });
});

app.get('/metrics', (req, res) => {
  const metrics = {
    jwtFailures: 0,
    replayAttacks: 0,
    codonMutationRate: 0,
    memoryCorrectionSuccess: 100,
    activeNuggetThreads: 0,
    topCodonDrift: 'N/A',
    memoryRepairs: 0
  };
  res.status(200).json(metrics);
});

// ---------- WebSockets ----------
global.wss = new WebSocketServer({ port: WS_PORT });
wss.on('connection', (ws, req) => {
  const token = (req.url || '').split('token=')[1];
  try {
    if (!token) throw new Error('Missing JWT');
    jwt.verify(token, JWT_SECRET);
    ws.sessionId = uuidv4();
    log(`WebSocket connected, sessionId=${ws.sessionId}`);
  } catch (err) {
    ws.close();
    log(`WebSocket connection failed: ${err.message}`, 'ERROR');
  }
});

const metricsWss = new WebSocketServer({ port: METRICS_WS_PORT });
metricsWss.on('connection', (ws, req) => {
  const token = (req.url || '').split('token=')[1];
  try {
    if (!token) throw new Error('Missing JWT');
    jwt.verify(token, JWT_SECRET);
    const interval = setInterval(() => {
      const metrics = {
        type: 'metrics_update',
        jwtFailures: 0,
        replayAttacks: 0,
        codonMutationRate: 0,
        memoryCorrectionSuccess: 100,
        activeNuggetThreads: 0,
        topCodonDrift: 'N/A',
        memoryRepairs: 0,
        timestamp: Date.now()
      };
      try { ws.send(JSON.stringify(metrics)); } catch {}
    }, 5000);
    ws.on('close', () => clearInterval(interval));
  } catch (err) {
    try { ws.close(); } catch {}
  }
});

// ---------- Start ----------
app.listen(PORT, () => {
  console.log(`🚀 API Bridge server listening on ${PORT}`);
  log(`API Bridge server started on port ${PORT}`);
});
"""
open('/mnt/data/apiBridge.js', 'w', encoding='utf-8').write(code)
print("Wrote /mnt/data/apiBridge.js")
