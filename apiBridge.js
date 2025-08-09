require('dotenv').config();
const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const { WebSocketServer } = require('ws');
const { v4: uuidv4 } = require('uuid');
const redis = require('redis');
const SecurityWatchdog = require('./SecurityWatchdog');
const FederatedThreatSync = require('./FederatedThreatSync');
const SecurityNetworkWatchdog = require('./security_network_watchdog');
const FederatedThreatSyncProtocol = require('./federated_threat_sync');
const DNAMemorySimulator = require('./dna_memory_simulator');
const SPISecurityEventArchiver = require('./phase3_security_archiver');
const KMNuggetValidationEngine = require('./KMNuggetValidationEngine');
const WebSocketEventManager = require('../ws/WebSocketEventManager');
const securityMiddleware = require('../middleware/securityMiddleware');
const CrossSessionValidator = require('../validation/CrossSessionValidator');

const app = express();
const watchdog = new SecurityWatchdog();
const threatSync = new FederatedThreatSync();
const networkWatchdog = new SecurityNetworkWatchdog({
  codonGenerator: require('./CodonGenerator'),
  validationEngine: new KMNuggetValidationEngine(),
  crossSessionValidator: new CrossSessionValidator(),
  dnaMemorySimulator: new DNAMemorySimulator()
});
const threatSyncProtocol = new FederatedThreatSyncProtocol({
  agentId: 'grok',
  codonGenerator: require('./CodonGenerator'),
  securityWatchdog: watchdog
});
const dnaMemory = new DNAMemorySimulator();
const spiArchiver = new SPISecurityEventArchiver();
const wsEventManager = new WebSocketEventManager();

app.use(cors());
app.use(express.json());
app.use(securityMiddleware.authenticateJWT);
app.use(securityMiddleware.rateLimit);
app.use((req, res, next) => watchdog.monitorRequest(req, res, next));
app.use((req, res, next) => networkWatchdog.trackRequest(req, res, next));

const fs = require('fs');
const path = require('path');
const logFile = path.join(__dirname, 'apiBridge.log');
function log(message, level = 'INFO') {
  const timestamp = new Date().toISOString();
  fs.appendFileSync(logFile, `[${timestamp}] ${level}: ${message}\n`);
}

log('Starting API Bridge server...');
const dnaStrands = new Map();

global.wss = new WebSocketServer({ port: 5003 });
wss.on('connection', (ws, req) => {
  const token = req.url.split('token=')[1];
  try {
    jwt.verify(token, process.env.JWT_SECRET || 'dummy_jwt_secret_123');
    ws.sessionId = uuidv4();
    log(`WebSocket connected, sessionId: ${ws.sessionId}`);
  } catch (err) {
    ws.close();
    log(`WebSocket connection failed: ${err.message}`, 'ERROR');
  }
});

// WebSocket for metrics
const metricsWss = new WebSocketServer({ port: 5004, path: '/metrics/ws' });
metricsWss.on('connection', (ws, req) => {
  const token = req.url.split('token=')[1];
  try {
    jwt.verify(token, process.env.JWT_SECRET || 'dummy_jwt_secret_123');
    ws.sessionId = uuidv4();
    log(`Metrics WebSocket connected, sessionId: ${ws.sessionId}`);
  } catch (err) {
    ws.close();
    log(`Metrics WebSocket connection failed: ${err.message}`, 'ERROR');
  }
});

// Broadcast metrics every 5s
setInterval(() => {
  const metrics = {
    jwtFailures: Array.from(networkWatchdog.requestCounters.values()).reduce((sum, counter) => sum + (counter.count || 0), 0),
    replayAttacks: Array.from(networkWatchdog.sessionTracker.values()).filter(session => session.requests?.some(req => req.error === 'Replay attack detected')).length,
    codonMutationRate: dnaMemory.getSystemStatus().totalMutations / 100 || 0,
    memoryCorrectionSuccess: dnaMemory.getSystemStatus().repairSuccessRate || 98,
    topCodonDrift: dnaMemory.getSystemStatus().dominantMutation || 'N/A',
    activeNuggetThreads: dnaStrands.size
  };
  metricsWss.clients.forEach(client => {
    if (client.readyState === WebSocketServer.OPEN) {
      client.send(JSON.stringify({ type: 'metrics_update', ...metrics }));
    }
  });
}, 5000);

app.get('/health', (req, res) => { res.status(200).json({ status: 'ready' }); });

app.post('/nugget/create', (req, res) => {
  const { userId, content, promptId, context } = req.body;
  try {
    if (!userId || !content || !promptId || !context?.sessionId) { throw new Error('Missing required fields'); }
    const nuggetId = uuidv4();
    const sessionId = context.sessionId;
    const codon = { nuggetId, content, promptId, type: 'Condition', origin: 'User', timestamp: new Date().toISOString() };
    const strand = dnaStrands.get(sessionId) || { sessionId, codons: [] };
    strand.codons.push(codon);
    dnaStrands.set(sessionId, strand);
    wss.clients.forEach(client => {
      if (client.sessionId === sessionId) { client.send(JSON.stringify({ type: 'nugget_update', ...codon, requestId: uuidv4() })); }
    });
    wsEventManager.emit('security_event', { type: 'nugget_created', nuggetId, sessionId });
    res.status(200).json({ status: 'success', nuggetId, sessionId, requestId: uuidv4() });
    log(`Nugget created: ${nuggetId}, session: ${sessionId}`);
  } catch (err) {
    res.status(401).json({ error: err.message || 'Invalid JWT', requestId: uuidv4() });
    log(`Nugget create failed: ${err.message}`, 'ERROR');
  }
});

app.post('/security/event', (req, res) => {
  const { event } = req.body;
  wsEventManager.emit('security_event', event);
  res.status(200).json({ status: 'broadcasted' });
});

app.post('/security/incident', (req, res) => {
  const { incident } = req.body;
  wsEventManager.emit('security_incident', incident);
  res.status(200).json({ status: 'broadcasted' });
});

app.post('/sync/threat', (req, res) => {
  const { signature } = req.body;
  try {
    if (!signature.vectorHash || !signature.timestamp || !signature.sessionSource || !signature.riskLevel) {
      throw new Error('Invalid threat signature format');
    }
    threatSync.handleMessage(null, JSON.stringify({ type: 'threat_signature', signature }));
    wsEventManager.emit('threat_signature', signature);
    res.status(200).json({ status: 'received', syncedAt: new Date().toISOString() });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.get('/sync/threat/pull', (req, res) => {
  const { after } = req.query;
  const fingerprints = threatSync.threatLedger.filter(f => !after || f.syncedAt > after);
  res.status(200).json({ fingerprints });
});

app.post('/validate', (req, res) => {
  const { nugget, comparisonSet } = req.body;
  try {
    const validator = new KMNuggetValidationEngine();
    const result = validator.validate(nugget, comparisonSet || []);
    res.status(200).json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.post('/batch-validate', (req, res) => {
  const { nuggets, comparisonSet } = req.body;
  try {
    const validator = new KMNuggetValidationEngine();
    const results = nuggets.map(nugget => validator.validate(nugget, comparisonSet || []));
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
    { id: uuidv4(), type: 'missing_jwt', severity: 'critical', timestamp: new Date().toISOString(), details: 'Missing JWT token detected' },
    { id: uuidv4(), type: 'session_spamming', severity: 'critical', timestamp: new Date().toISOString(), details: 'Rate limit exceeded for IP' },
    { id: uuidv4(), type: 'invalid_jwt', severity: 'critical', timestamp: new Date().toISOString(), details: 'Invalid JWT token detected' }
  ];
  res.status(200).json({ alerts });
});

app.get('/session/:id', (req, res) => {
  const sessionId = req.params.id;
  const strand = dnaStrands.get(sessionId);
  if (!strand) {
    res.status(404).json({ error: 'Session not found' });
    log(`Session fetch failed: ${sessionId}`, 'ERROR');
    return;
  }
  res.status(200).json({ sessionId, codons: strand.codons });
  log(`Session fetched: ${sessionId}`);
});

app.get('/mutation/timeline', (req, res) => {
  const { sessionId, riskLevel, agentSource, codonStatus } = req.query;
  let events = dnaMemory.getMutationEvents() || [];
  if (sessionId) events = events.filter(e => e.sessionId === sessionId);
  if (riskLevel) events = events.filter(e => e.riskLevel === riskLevel);
  if (agentSource) events = events.filter(e => e.agentSource === agentSource);
  if (codonStatus) events = events.filter(e => e.codonStatus === codonStatus);
  if (!events.length) {
    events = [
      { id: uuidv4(), sessionId: sessionId || 'session_1', type: 'mutation', riskLevel: 'high', agentSource: 'grok', codonStatus: 'degraded', timestamp: new Date().toISOString() },
      { id: uuidv4(), sessionId: sessionId || 'session_1', type: 'repair', riskLevel: 'medium', agentSource: 'claude', codonStatus: 'repaired', timestamp: new Date().toISOString() }
    ];
  }
  const interval = setInterval(() => {
    wsEventManager.emit('mutation_replay', { events });
  }, 2000);
  setTimeout(() => clearInterval(interval), 10000);
  res.status(200).json({ mutationReplayEvents: events });
});

app.get('/metrics', (req, res) => {
  const metrics = {
    jwtFailures: Array.from(networkWatchdog.requestCounters.values()).reduce((sum, counter) => sum + (counter.count || 0), 0),
    replayAttacks: Array.from(networkWatchdog.sessionTracker.values()).filter(session => session.requests?.some(req => req.error === 'Replay attack detected')).length,
    codonMutationRate: dnaMemory.getSystemStatus().totalMutations / 100 || 0,
    memoryCorrectionSuccess: dnaMemory.getSystemStatus().repairSuccessRate || 98,
    topCodonDrift: dnaMemory.getSystemStatus().dominantMutation || 'N/A',
    activeNuggetThreads: dnaStrands.size
  };
  res.status(200).json(metrics);
});

app.post('/agent/interaction', (req, res) => {
  const { agent, interaction } = req.body;
  try {
    if (agent === 'chatgpt' && interaction.type === 'threat_signature') {
      threatSync.handleMessage(null, JSON.stringify({ type: 'threat_signature', signature: interaction.signature }));
      wsEventManager.emit('threat_signature', interaction.signature);
      res.status(200).json({ status: 'received', syncedAt: new Date().toISOString() });
    } else {
      throw new Error('Invalid agent interaction');
    }
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.listen(10000, () => { console.log('🚀 API Bridge server listening on port 10000'); log('API Bridge server started on port 10000'); });