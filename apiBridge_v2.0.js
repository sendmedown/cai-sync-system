
// apiBridge.js - Comprehensive Integration v2.0
// Integrates: KMNuggetValidationEngine, PromptChainRouter, CrossSessionValidator, CodonGenerator, WebSocketValidationEvents
console.log('🚀 Starting Bio-Quantum Trading Platform API Bridge v2.0...');

const express = require('express');
const { Server } = require('ws');
const { v4: uuidv4 } = require('uuid');
const jwt = require('jsonwebtoken');

// Import all components
const KMNuggetValidationEngine = require('./KMNuggetValidationEngine.js');
const PromptChainRouter = require('./promptChainRouter.js');
const CrossSessionValidator = require('./CrossSessionValidator.js');
const CodonGenerator = require('./CodonGenerator.js');
const { WebSocketValidationEvents, EVENT_TYPES } = require('./WebSocketValidationEvents.js');

const app = express();
app.use(express.json());

// JWT secret
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

// In-memory DNA strands for session tracking
const dnaStrands = new Map();

// Initialize all engines
const validationEngine = new KMNuggetValidationEngine();
const promptChainRouter = new PromptChainRouter({
  chainConfigPath: './shared/prompt_chain_system.json',
  timeout: 300000,
  maxConcurrentChains: 10
});
const crossSessionValidator = new CrossSessionValidator({
  conflictThreshold: 0.7,
  maxHistorySize: 10000,
  semanticSimilarityThreshold: 0.8
});
const codonGenerator = new CodonGenerator({
  dnaStrands: dnaStrands,
  autoStore: true
});

// Initialize WebSocket server
const server = app.listen(process.env.PORT || 10000, '0.0.0.0', () => {
  console.log(`🌐 Server running on port ${process.env.PORT || 10000}`);
});
const wss = new Server({ server });
global.wss = wss;

// Initialize WebSocket event broadcaster
const wsEvents = new WebSocketValidationEvents(wss);

// Initialize all engines
async function initializeEngines() {
  try {
    console.log('🔄 Initializing all engines...');
    
    await validationEngine.initialize();
    await promptChainRouter.initialize();  
    await crossSessionValidator.initialize();
    await codonGenerator.initialize();
    
    console.log('✅ All engines initialized successfully');
  } catch (error) {
    console.error('❌ Engine initialization failed:', error);
    process.exit(1);
  }
}

initializeEngines();
