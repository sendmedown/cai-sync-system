const { v4: uuidv4 } = require('uuid');
const crypto = require('crypto');

class CrossSessionValidator {
  constructor(options = {}) {
    this.sessionStore = new Map();
    this.maxSessionAge = options.maxSessionAge || 3600000;
    this.initialize();
  }

  initialize() {
    console.log('ðŸ” CrossSessionValidator initialized');
  }

  validateSession(sessionId, requestData) {
    const session = this.sessionStore.get(sessionId);
    if (!session || Date.now() - session.created > this.maxSessionAge) {
      return { valid: false, error: 'Session expired or invalid' };
    }

    const hash = this.generateRequestHash(requestData);
    if (session.requests.includes(hash)) {
      return { valid: false, error: 'Replay attack detected' };
    }

    session.requests.push(hash);
    this.sessionStore.set(sessionId, session);
    return { valid: true };
  }

  generateRequestHash(requestData) {
    return crypto.createHash('sha256').update(JSON.stringify(requestData)).digest('hex');
  }

  addSession(sessionId) {
    this.sessionStore.set(sessionId, {
      id: sessionId,
      created: Date.now(),
      requests: []
    });
  }
}

module.exports = CrossSessionValidator;
