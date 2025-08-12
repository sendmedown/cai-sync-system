const { EventEmitter } = require('events');
const { WebSocketServer } = require('ws');

class WebSocketEventManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.wss = global.wss || new WebSocketServer({ port: options.port || 5003 });
    this.initialize();
  }

  initialize() {
    console.log('ðŸ”— WebSocketEventManager initialized');
    
    this.wss.on('connection', (ws, req) => {
      const token = req.url.split('token=')[1];
      try {
        require('jsonwebtoken').verify(token, process.env.JWT_SECRET || 'dummy_jwt_secret_123');
        ws.sessionId = require('uuid').v4();
        console.log(`ðŸ”Œ WebSocket connected, sessionId: ${ws.sessionId}`);
        ws.send(JSON.stringify({ type: 'init', status: 'connected' }));
      } catch (err) {
        ws.close();
        console.error(`âŒ WebSocket connection failed: ${err.message}`);
      }
    });

    this.on('security_event', (event) => {
      this.broadcast({ type: 'security_event', event });
    });

    this.on('security_incident', (incident) => {
      this.broadcast({ type: 'security_incident', incident });
    });

    this.on('threat_signature', (signature) => {
      this.broadcast({ type: 'threat_signature', signature });
    });
  }

  broadcast(data) {
    this.wss.clients.forEach(client => {
      if (client.readyState === WebSocketServer.OPEN) {
        client.send(JSON.stringify(data));
      }
    });
  }
}

module.exports = WebSocketEventManager;
