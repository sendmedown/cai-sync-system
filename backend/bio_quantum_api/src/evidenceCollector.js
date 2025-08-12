const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');

class BioQuantumEvidenceCollector {
  constructor(options = {}) {
    this.collectorId = 'bioq_evidence_collector_v2';
    this.config = {
      maxRingBufferSize: options.maxRingBufferSize || 1000,
      evidenceRetentionHours: options.evidenceRetention || 72,
      fileSystemStorage: options.enableFileStorage || true,
      redisStorage: options.enableRedisStorage || false,
      evidenceDirectory: options.evidenceDir || './evidence'
    };
    
    this.evidenceRingBuffer = [];
    this.evidenceIndex = new Map();
    this.incidentEvidence = new Map();
    this.collectionStats = {
      totalEvidence: 0,
      evidenceByType: {}
    };
    
    this.initializeEvidenceCollection();
  }

  async initializeEvidenceCollection() {
    try {
      if (this.config.fileSystemStorage) {
        await fs.mkdir(this.config.evidenceDirectory, { recursive: true });
      }
      console.log('ðŸ“ Bio-Quantum Evidence Collector initialized');
    } catch (error) {
      console.error('âŒ Evidence collector initialization failed:', error);
    }
  }

  async collectEvidence(securityEvent, incidentId = null) {
    const evidenceId = crypto.randomUUID();
    const timestamp = new Date().toISOString();
    
    const evidence = {
      evidenceId,
      timestamp,
      incidentId,
      securityEvent: {
        ...securityEvent,
        metadata: {
          ...securityEvent.metadata,
          authToken: '[REDACTED]'
        }
      },
      metadata: {
        collectorId: this.collectorId
      }
    };
    
    this.evidenceRingBuffer.push(evidence);
    this.evidenceIndex.set(evidenceId, evidence);
    
    console.log(`ðŸ“‹ Evidence collected: ${evidenceId}`);
    return { evidenceId, collected: true };
  }
}

module.exports = BioQuantumEvidenceCollector;
