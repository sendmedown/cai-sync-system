const { EventEmitter } = require('events');
const WebSocket = require('ws');
const crypto = require('crypto');

class FederatedThreatSyncProtocol extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.config = {
      agentId: options.agentId || 'claude',
      syncInterval: options.syncInterval || 30000,
      maxFingerprintAge: options.maxFingerprintAge || 3600000,
      trustThreshold: options.trustThreshold || 0.6,
      encryptionKey: options.encryptionKey || process.env.FEDERATION_KEY,
      syncEndpoints: options.syncEndpoints || {
        claude: 'ws://claude-sync.bio-quantum.ai',
        grok: 'ws://grok-sync.bio-quantum.ai',
        chatgpt: 'ws://chatgpt-sync.bio-quantum.ai'
      },
      ...options
    };

    this.connectedAgents = new Map();
    this.sharedFingerprints = new Map();
    this.pendingSyncs = new Set();
    this.trustScores = new Map();
    this.syncHistory = [];
    
    this.dnaMemorySimulator = options.dnaMemorySimulator;
    this.securityWatchdog = options.securityWatchdog;
    this.codonGenerator = options.codonGenerator;
    
    this.isInitialized = false;
    this.lastSyncTimestamp = 0;
    
    this.initializeFederation();
  }

  async initializeFederation() {
    console.log(`ðŸ“¡ Initializing Federated Threat Sync for agent: ${this.config.agentId}`);
    
    try {
      await this.connectToFederatedAgents();
      this.startPeriodicSync();
      this.startThreatBroadcasting();
      this.startTrustManagement();
      
      this.isInitialized = true;
      console.log('ðŸŒ Federated Threat Sync Protocol operational');
      this.emit('federation_ready', { agentId: this.config.agentId, timestamp: Date.now() });
    } catch (error) {
      console.error('âŒ Federation initialization failed:', error);
      this.emit('federation_error', { error: error.message, timestamp: Date.now() });
    }
  }

  async connectToFederatedAgents() {
    const connectionPromises = [];
    
    Object.entries(this.config.syncEndpoints).forEach(([agentName, endpoint]) => {
      if (agentName !== this.config.agentId) {
        connectionPromises.push(this.connectToAgent(agentName, endpoint));
      }
    });
    
    await Promise.allSettled(connectionPromises);
    console.log(`ðŸ”— Connected to ${this.connectedAgents.size} federated agents`);
  }

  async connectToAgent(agentName, endpoint) {
    try {
      const ws = new WebSocket(endpoint, {
        headers: {
          'Agent-ID': this.config.agentId,
          'Protocol-Version': '1.0',
          'Authentication': this.generateAuthToken(agentName)
        }
      });

      ws.on('open', () => {
        console.log(`âœ… Connected to ${agentName}`);
        this.connectedAgents.set(agentName, {
          connection: ws,
          status: 'connected',
          lastPing: Date.now(),
          syncCount: 0
        });
        this.initializeTrustScore(agentName);
        this.sendHandshake(agentName);
      });

      ws.on('message', (data) => {
        this.handleIncomingMessage(agentName, data);
      });

      ws.on('close', () => {
        console.log(`âŒ Disconnected from ${agentName}`);
        this.handleAgentDisconnection(agentName);
      });

      ws.on('error', (error) => {
        console.error(`âš ï¸ Connection error with ${agentName}:`, error);
      });

    } catch (error) {
      console.error(`Failed to connect to ${agentName}:`, error);
    }
  }

  startPeriodicSync() {
    setInterval(async () => {
      if (this.connectedAgents.size > 0) {
        await this.performFederatedSync();
      }
    }, this.config.syncInterval);
  }

  startThreatBroadcasting() {
    if (this.securityWatchdog) {
      this.securityWatchdog.on('threat_detected', async (event) => {
        await this.broadcastThreatFingerprint(event.threat);
      });
    }

    if (this.dnaMemorySimulator) {
      this.dnaMemorySimulator.on('threat_stored', async (fingerprint) => {
        await this.broadcastThreatFingerprint(fingerprint);
      });
    }
  }

  startTrustManagement() {
    setInterval(() => {
      this.updateTrustScores();
      this.cleanupExpiredFingerprints();
    }, this.config.syncInterval * 2);
  }

  async performFederatedSync() {
    const syncId = `sync_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`;
    this.pendingSyncs.add(syncId);
    
    try {
      const localFingerprints = await this.collectLocalFingerprints();
      const syncPackage = this.createSyncPackage(syncId, localFingerprints);
      
      await this.broadcastSyncPackage(syncPackage);
      this.lastSyncTimestamp = Date.now();
      
      this.emit('sync_completed', { syncId, fingerprints: localFingerprints.length });
    } catch (error) {
      console.error(`âŒ Sync failed for ${syncId}:`, error);
      this.emit('sync_error', { syncId, error: error.message });
    } finally {
      this.pendingSyncs.delete(syncId);
    }
  }

  async collectLocalFingerprints() {
    const fingerprints = [];
    
    if (this.dnaMemorySimulator) {
      const recentThreats = Array.from(this.dnaMemorySimulator.threatFingerprints.values())
        .filter(fp => Date.now() - fp.timestamp < this.config.maxFingerprintAge);
      fingerprints.push(...recentThreats.map(fp => this.convertToCodonFingerprint(fp)));
    }

    if (this.securityWatchdog) {
      const watchdogThreats = Array.from(this.securityWatchdog.threatSignatures.values())
        .filter(threat => Date.now() - threat.timestamp < this.config.maxFingerprintAge);
      fingerprints.push(...watchdogThreats.map(threat => this.convertThreatToCodonFingerprint(threat)));
    }
    
    return fingerprints;
  }

  convertToCodonFingerprint(threat) {
    return {
      id: threat.id || this.generateFingerprintId(threat),
      format_version: "1.0",
      agent_source: this.config.agentId,
      timestamp: threat.timestamp,
      codon_signature: {
        pattern: this.generateCodonPattern(threat),
        classification: threat.type || 'unknown',
        severity: threat.severity || 'medium',
        confidence: threat.confidence || 0.7
      },
      vector_data: {
        type: threat.vector?.type || 'generic',
        endpoints: threat.endpoints || [],
        ips: threat.ips || [],
        signatures: threat.signatures || []
      },
      metadata: {
        detection_method: threat.metadata?.detection_method || 'automatic',
        false_positive_rate: threat.metadata?.false_positive_rate || 0.1,
        correlation_id: threat.metadata?.correlation_id
      }
    };
  }

  convertThreatToCodonFingerprint(threat) {
    return {
      id: `watchdog_${threat.type}_${threat.timestamp}`,
      format_version: "1.0",
      agent_source: this.config.agentId,
      timestamp: threat.timestamp,
      codon_signature: {
        pattern: this.generateThreatCodonPattern(threat),
        classification: threat.type,
        severity: threat.severity,
        confidence: 0.8
      },
      vector_data: {
        type: threat.type,
        endpoint: threat.endpoint,
        details: threat.details,
        session_id: threat.sessionId
      },
      metadata: {
        detection_method: 'security_watchdog',
        source: 'bio_quantum_platform'
      }
    };
  }

  generateCodonPattern(threat) {
    const data = JSON.stringify(threat);
    const hash = crypto.createHash('sha256').update(data).digest('hex');
    const codonPattern = [];
    
    for (let i = 0; i < hash.length; i += 8) {
      const segment = hash.substr(i, 8);
      codonPattern.push({
        position: i / 8,
        codon: segment,
        weight: parseInt(segment.substr(0, 2), 16) / 255
      });
    }
    
    return codonPattern;
  }

  generateThreatCodonPattern(threat) {
    const components = [
      threat.type,
      threat.severity,
      threat.timestamp
    ];
    
    const hash = crypto.createHash('sha256').update(components.join('')).digest('hex');
    const codonPattern = [];
    
    for (let i = 0; i < hash.length; i += 8) {
      const segment = hash.substr(i, 8);
      codonPattern.push({
        position: i / 8,
        codon: segment,
        weight: parseInt(segment.substr(0, 2), 16) / 255
      });
    }
    
    return codonPattern;
  }

  generateFingerprintId(threat) {
    return `fingerprint_${crypto.createHash('sha256').update(JSON.stringify(threat)).digest('hex').slice(0, 16)}`;
  }

  generateAuthToken(agentName) {
    const payload = {
      agentId: this.config.agentId,
      timestamp: Date.now(),
      targetAgent: agentName
    };
    
    return crypto.createHmac('sha256', this.config.encryptionKey || 'default_key')
      .update(JSON.stringify(payload)).digest('hex');
  }

  async broadcastThreatFingerprint(fingerprint) {
    const syncPackage = {
      type: 'threat_signature',
      signature: fingerprint,
      source: this.config.agentId,
      timestamp: Date.now()
    };

    this.connectedAgents.forEach((agent, agentName) => {
      if (agent.status === 'connected') {
        agent.connection.send(JSON.stringify(syncPackage));
        console.log(`ðŸ“¡ Sent threat fingerprint to ${agentName}`);
      }
    });
  }

  async broadcastSyncPackage(syncPackage) {
    this.connectedAgents.forEach((agent, agentName) => {
      if (agent.status === 'connected') {
        agent.connection.send(JSON.stringify(syncPackage));
        agent.syncCount++;
        console.log(`ðŸ“¤ Sent sync package to ${agentName}, count: ${agent.syncCount}`);
      }
    });
  }

  createSyncPackage(syncId, fingerprints) {
    return {
      type: 'federated_sync',
      syncId,
      fingerprints,
      source: this.config.agentId,
      timestamp: Date.now()
    };
  }

  initializeTrustScore(agentName) {
    this.trustScores.set(agentName, {
      score: 0.5,
      lastUpdate: Date.now(),
      successfulSyncs: 0,
      failedSyncs: 0,
      lastValidation: null
    });
  }

  updateTrustScores() {
    this.trustScores.forEach((score, agentName) => {
      const agent = this.connectedAgents.get(agentName);
      if (agent) {
        const timeSinceLastSync = Date.now() - agent.lastPing;
        const syncSuccessRate = agent.syncCount > 0 ? 
          agent.syncCount / (agent.syncCount + score.failedSyncs) : 0;
        
        const newScore = Math.min(1, Math.max(0, 
          score.score + (syncSuccessRate - 0.5) * 0.1 - timeSinceLastSync / 3600000
        ));
        
        score.score = newScore;
        score.lastUpdate = Date.now();
        
        if (newScore < this.config.trustThreshold) {
          console.warn(`âš ï¸ Trust score for ${agentName} below threshold: ${newScore}`);
        }
      }
    });
  }

  cleanupExpiredFingerprints() {
    const now = Date.now();
    this.sharedFingerprints.forEach((fingerprint, id) => {
      if (now - fingerprint.timestamp > this.config.maxFingerprintAge) {
        this.sharedFingerprints.delete(id);
        console.log(`ðŸ—‘ï¸ Removed expired fingerprint: ${id}`);
      }
    });
  }

  async handleIncomingMessage(agentName, data) {
    try {
      const message = JSON.parse(data);
      
      if (message.type === 'threat_signature') {
        const trustScore = this.trustScores.get(agentName)?.score || 0;
        if (trustScore < this.config.trustThreshold) {
          console.warn(`ðŸš« Dropped low-trust signature from ${agentName}`);
          return;
        }
        
        this.sharedFingerprints.set(message.signature.id, message.signature);
        this.syncHistory.push({
          agentName,
          signatureId: message.signature.id,
          receivedAt: Date.now()
        });
        
        console.log(`ðŸ“¥ Received threat signature from ${agentName}: ${message.signature.id}`);
        this.emit('new_signature', { agentName, signature: message.signature });
        
      } else if (message.type === 'federated_sync') {
        message.fingerprints.forEach(fingerprint => {
          this.sharedFingerprints.set(fingerprint.id, fingerprint);
        });
        
        this.syncHistory.push({
          agentName,
          syncId: message.syncId,
          fingerprintCount: message.fingerprints.length,
          receivedAt: Date.now()
        });
        
        console.log(`ðŸ“¦ Received sync package from ${agentName}: ${message.syncId}`);
        this.emit('sync_received', { 
          agentName, 
          syncId: message.syncId, 
          fingerprints: message.fingerprints 
        });
      }
    } catch (error) {
      console.error(`âŒ Error processing message from ${agentName}:`, error);
    }
  }

  handleAgentDisconnection(agentName) {
    const agent = this.connectedAgents.get(agentName);
    if (agent) {
      agent.status = 'disconnected';
      agent.lastPing = Date.now();
      this.connectedAgents.set(agentName, agent);
      
      console.log(`ðŸ”Œ Agent ${agentName} disconnected, trust score: ${this.trustScores.get(agentName)?.score || 0}`);
      this.emit('agent_disconnected', { agentName, timestamp: Date.now() });
    }
  }
}

module.exports = FederatedThreatSyncProtocol;
