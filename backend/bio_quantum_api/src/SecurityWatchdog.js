const jwt = require('jsonwebtoken');
const { WebSocketServer } = require('ws');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');

class SecurityWatchdog {
  constructor(options = {}) {
    this.wss = global.wss || new WebSocketServer({ port: options.port || 5005 });
    this.alertFile = path.join(__dirname, '../../shared/threatAlerts.json');
    this.threatAlerts = [];
    this.requestCounts = new Map();
    this.initialize();
  }

  initialize() {
    console.log('ðŸ” Security Watchdog initialized');
    this.wss.on('connection', (ws) => {
      ws.send(JSON.stringify({ type: 'init', alerts: this.threatAlerts }));
    });
  }

  async monitorRequest(req, res, next) {
    const token = req.headers.authorization?.split(' ')[1];
    const ip = req.ip;
    const sessionId = req.query.sessionId || 'unknown';
    const alert = {
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      ip,
      sessionId,
      threatLevel: 'low'
    };

    if (!token) {
      alert.threatLevel = 'critical';
      alert.eventType = 'missing_jwt';
      this.logThreat(alert);
      return res.status(401).json({ error: 'Missing JWT' });
    }

    try {
      jwt.verify(token, process.env.JWT_SECRET || 'dummy_jwt_secret_123');
      
      const count = (this.requestCounts.get(ip) || 0) + 1;
      this.requestCounts.set(ip, count);
      
      if (count > 100) {
        alert.threatLevel = 'critical';
        alert.eventType = 'session_spamming';
        this.logThreat(alert);
        return res.status(429).json({ error: 'Rate limit exceeded' });
      }
      
      next();
    } catch (err) {
      alert.threatLevel = 'critical';
      alert.eventType = 'invalid_jwt';
      this.logThreat(alert);
      return res.status(401).json({ error: 'Invalid JWT' });
    }
  }

  async logThreat(alert) {
    this.threatAlerts.push(alert);
    await fs.writeFile(this.alertFile, JSON.stringify(this.threatAlerts, null, 2));
    
    this.wss.clients.forEach(client => {
      if (client.readyState === WebSocketServer.OPEN) {
        client.send(JSON.stringify({ type: 'security_alert', alert }));
      }
    });
    
    console.log(`ðŸš¨ Threat detected: ${alert.eventType}, Level: ${alert.threatLevel}`);
  }
}

module.exports = SecurityWatchdog;
