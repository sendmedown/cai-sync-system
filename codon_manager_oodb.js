/**
 * CodonManagerOODB.js
 * Phase 8 - Object-Oriented Database Manager for DNA-Codon Memory Architecture
 * GenesisAiX Bio-Quantum AI Trading Platform
 * 
 * Implements hybrid Redis + in-memory object model + persistent NoSQL mirror
 * Supports dynamic DNA schemas, nested codons, and evolving KM Nugget structures
 */

const Redis = require('redis');
const { EventEmitter } = require('events');

class CodonManagerOODB extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      redis: {
        host: config.redisHost || 'localhost',
        port: config.redisPort || 6379,
        ttl: config.redisTTL || 3600 // 1 hour default
      },
      memory: {
        maxObjects: config.maxMemoryObjects || 10000,
        gcThreshold: config.gcThreshold || 0.8
      },
      persistence: {
        syncInterval: config.syncInterval || 30000, // 30 seconds
        backupPath: config.backupPath || './codon_backup'
      }
    };

    // Three-tier storage
    this.redisClient = null;
    this.memoryStore = new Map(); // In-memory object graph
    this.persistentMirror = new Map(); // NoSQL mirror for durability
    
    // Schema and metadata
    this.codonSchema = null;
    this.mutationHistory = [];
    this.agentMemoryScopes = new Map();
    
    // Performance tracking
    this.stats = {
      reads: 0,
      writes: 0,
      mutations: 0,
      cacheHits: 0,
      cacheMisses: 0
    };

    this.initialized = false;
  }

  /**
   * Initialize the OODB system with Redis connection and schema loading
   */
  async initialize(codonSchemaPath = './codonSchema.json') {
    try {
      // Connect to Redis
      this.redisClient = Redis.createClient(this.config.redis);
      await this.redisClient.connect();
      
      // Load codon schema
      if (require('fs').existsSync(codonSchemaPath)) {
        this.codonSchema = require(codonSchemaPath);
        console.log('✅ Codon schema loaded:', Object.keys(this.codonSchema).length, 'types');
      }
      
      // Start background sync process
      this.startPersistenceSync();
      
      this.initialized = true;
      this.emit('initialized');
      console.log('🧬 CodonManagerOODB initialized successfully');
      
    } catch (error) {
      console.error('❌ Failed to initialize CodonManagerOODB:', error);
      throw error;
    }
  }

  /**
   * Create a new codon object with DNA-based structure
   */
  async createCodon(codonId, dnaSequence, metadata = {}) {
    if (!this.initialized) throw new Error('CodonManagerOODB not initialized');
    
    const codon = {
      id: codonId,
      dnaSequence,
      metadata,
      created: new Date().toISOString(),
      mutations: [],
      kmNuggets: [],
      agentScope: metadata.agentId || 'global',
      semanticLinks: new Set(),
      auditTrail: [{
        action: 'created',
        timestamp: new Date().toISOString(),
        agent: metadata.agentId
      }]
    };

    // Validate against schema if available
    if (this.codonSchema && !this.validateCodonStructure(codon)) {
      throw new Error('Codon structure validation failed');
    }

    // Store in all three tiers
    await this.storeCodon(codon);
    
    // Track agent memory scope
    this.trackAgentMemoryScope(codon.agentScope, codonId);
    
    this.stats.writes++;
    this.emit('codonCreated', codon);
    
    return codon;
  }

  /**
   * Retrieve codon with intelligent caching strategy
   */
  async getCodon(codonId) {
    if (!this.initialized) throw new Error('CodonManagerOODB not initialized');
    
    // 1. Check in-memory store first (fastest)
    if (this.memoryStore.has(codonId)) {
      this.stats.reads++;
      this.stats.cacheHits++;
      return this.memoryStore.get(codonId);
    }

    // 2. Check Redis cache
    try {
      const redisData = await this.redisClient.get(`codon:${codonId}`);
      if (redisData) {
        const codon = JSON.parse(redisData);
        // Restore Set objects
        codon.semanticLinks = new Set(codon.semanticLinks);
        
        // Cache in memory for future access
        this.cacheInMemory(codonId, codon);
        
        this.stats.reads++;
        this.stats.cacheHits++;
        return codon;
      }
    } catch (redisError) {
      console.warn('Redis read error:', redisError.message);
    }

    // 3. Fall back to persistent mirror
    if (this.persistentMirror.has(codonId)) {
      const codon = this.persistentMirror.get(codonId);
      
      // Cache in both Redis and memory
      await this.cacheCodon(codonId, codon);
      
      this.stats.reads++;
      this.stats.cacheMisses++;
      return codon;
    }

    this.stats.reads++;
    this.stats.cacheMisses++;
    return null;
  }

  /**
   * Mutate codon and track changes for auditability
   */
  async mutateCodon(codonId, mutation, agentId) {
    const codon = await this.getCodon(codonId);
    if (!codon) throw new Error(`Codon ${codonId} not found`);

    const mutationRecord = {
      id: `mut_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      agentId,
      type: mutation.type,
      changes: mutation.changes,
      reasoning: mutation.reasoning || null
    };

    // Apply mutation
    codon.mutations.push(mutationRecord);
    codon.auditTrail.push({
      action: 'mutated',
      timestamp: mutationRecord.timestamp,
      agent: agentId,
      mutationId: mutationRecord.id
    });

    // Update codon properties based on mutation type
    this.applyMutation(codon, mutation);

    // Store updated codon
    await this.storeCodon(codon);
    
    // Track global mutation history
    this.mutationHistory.push(mutationRecord);
    
    this.stats.mutations++;
    this.emit('codonMutated', { codon, mutation: mutationRecord });
    
    return codon;
  }

  /**
   * Add KM Nugget to codon for knowledge management
   */
  async addKMNugget(codonId, nugget, agentId) {
    const codon = await this.getCodon(codonId);
    if (!codon) throw new Error(`Codon ${codonId} not found`);

    const kmNugget = {
      id: `km_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content: nugget.content,
      type: nugget.type || 'general',
      confidence: nugget.confidence || 0.8,
      agentId,
      timestamp: new Date().toISOString(),
      semanticTags: nugget.tags || []
    };

    codon.kmNuggets.push(kmNugget);
    codon.auditTrail.push({
      action: 'km_nugget_added',
      timestamp: kmNugget.timestamp,
      agent: agentId,
      nuggetId: kmNugget.id
    });

    await this.storeCodon(codon);
    this.emit('kmNuggetAdded', { codon, nugget: kmNugget });
    
    return kmNugget;
  }

  /**
   * Create semantic links between codons
   */
  async linkCodons(codonId1, codonId2, linkType = 'semantic', strength = 1.0) {
    const codon1 = await this.getCodon(codonId1);
    const codon2 = await this.getCodon(codonId2);
    
    if (!codon1 || !codon2) {
      throw new Error('One or both codons not found');
    }

    const linkData = `${codonId2}:${linkType}:${strength}`;
    codon1.semanticLinks.add(linkData);
    
    const reverseLinkData = `${codonId1}:${linkType}:${strength}`;
    codon2.semanticLinks.add(reverseLinkData);

    await Promise.all([
      this.storeCodon(codon1),
      this.storeCodon(codon2)
    ]);

    this.emit('codonsLinked', { codon1: codonId1, codon2: codonId2, linkType, strength });
  }

  /**
   * Query codons by agent memory scope
   */
  async getCodonsByAgentScope(agentId) {
    const scopeCodonIds = this.agentMemoryScopes.get(agentId) || new Set();
    const codons = [];
    
    for (const codonId of scopeCodonIds) {
      const codon = await this.getCodon(codonId);
      if (codon) codons.push(codon);
    }
    
    return codons;
  }

  /**
   * Get mutation history with filtering options
   */
  getMutationHistory(filter = {}) {
    let history = [...this.mutationHistory];
    
    if (filter.agentId) {
      history = history.filter(m => m.agentId === filter.agentId);
    }
    
    if (filter.type) {
      history = history.filter(m => m.type === filter.type);
    }
    
    if (filter.since) {
      const sinceDate = new Date(filter.since);
      history = history.filter(m => new Date(m.timestamp) >= sinceDate);
    }
    
    return history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  }

  /**
   * Get system statistics and performance metrics
   */
  getStats() {
    return {
      ...this.stats,
      memoryObjects: this.memoryStore.size,
      persistentObjects: this.persistentMirror.size,
      agentScopes: this.agentMemoryScopes.size,
      totalMutations: this.mutationHistory.length,
      cacheHitRate: this.stats.reads > 0 ? (this.stats.cacheHits / this.stats.reads) : 0
    };
  }

  // ===== Private Methods =====

  async storeCodon(codon) {
    // Convert Set to Array for JSON serialization
    const serializable = {
      ...codon,
      semanticLinks: Array.from(codon.semanticLinks)
    };

    // Store in all three tiers
    this.memoryStore.set(codon.id, codon);
    this.persistentMirror.set(codon.id, codon);
    
    try {
      await this.redisClient.setEx(
        `codon:${codon.id}`, 
        this.config.redis.ttl, 
        JSON.stringify(serializable)
      );
    } catch (redisError) {
      console.warn('Redis write error:', redisError.message);
    }

    // Memory management
    this.manageMemorySize();
  }

  async cacheCodon(codonId, codon) {
    this.cacheInMemory(codonId, codon);
    
    try {
      const serializable = {
        ...codon,
        semanticLinks: Array.from(codon.semanticLinks)
      };
      await this.redisClient.setEx(
        `codon:${codonId}`, 
        this.config.redis.ttl, 
        JSON.stringify(serializable)
      );
    } catch (redisError) {
      console.warn('Redis cache error:', redisError.message);
    }
  }

  cacheInMemory(codonId, codon) {
    this.memoryStore.set(codonId, codon);
    this.manageMemorySize();
  }

  manageMemorySize() {
    if (this.memoryStore.size > this.config.memory.maxObjects * this.config.memory.gcThreshold) {
      // Simple LRU-style cleanup - remove oldest entries
      const entries = Array.from(this.memoryStore.entries());
      const toRemove = Math.floor(this.memoryStore.size * 0.2); // Remove 20%
      
      for (let i = 0; i < toRemove; i++) {
        this.memoryStore.delete(entries[i][0]);
      }
      
      console.log(`🧹 Memory cleanup: removed ${toRemove} objects`);
    }
  }

  validateCodonStructure(codon) {
    // Basic validation against schema
    if (!this.codonSchema) return true;
    
    const requiredFields = ['id', 'dnaSequence', 'created'];
    return requiredFields.every(field => codon.hasOwnProperty(field));
  }

  applyMutation(codon, mutation) {
    switch (mutation.type) {
      case 'dna_update':
        codon.dnaSequence = mutation.changes.newSequence;
        break;
      case 'metadata_update':
        Object.assign(codon.metadata, mutation.changes);
        break;
      case 'semantic_enhancement':
        if (mutation.changes.tags) {
          codon.semanticTags = [...(codon.semanticTags || []), ...mutation.changes.tags];
        }
        break;
      default:
        console.warn('Unknown mutation type:', mutation.type);
    }
  }

  trackAgentMemoryScope(agentId, codonId) {
    if (!this.agentMemoryScopes.has(agentId)) {
      this.agentMemoryScopes.set(agentId, new Set());
    }
    this.agentMemoryScopes.get(agentId).add(codonId);
  }

  startPersistenceSync() {
    setInterval(() => {
      this.syncToPersistentStorage();
    }, this.config.persistence.syncInterval);
  }

  async syncToPersistentStorage() {
    // In a real implementation, this would sync to MongoDB, CouchDB, etc.
    // For now, we just ensure the persistent mirror is current
    console.log(`🔄 Sync: ${this.persistentMirror.size} objects in persistent storage`);
  }

  async close() {
    if (this.redisClient) {
      await this.redisClient.quit();
    }
    this.emit('closed');
  }
}

module.exports = CodonManagerOODB;