const axios = require('axios');

const demoPromptPack = {
  "demo-session-001": {
    sessionId: "demo-session-001",
    sessionName: "Smart AAPL Momentum Strategy",
    description: "Well-structured momentum trading with proper risk management",
    nuggets: [
      {
        nuggetId: "nugget-001-001",
        sessionId: "demo-session-001",
        promptId: "prompt-001",
        userId: "Richard",
        content: "Monitor AAPL when RSI drops below 30 and volume exceeds 50M shares",
        type: "Condition",
        origin: "User",
        semanticIndex: ["AAPL", "RSI", "<30", "volume", ">50M", "oversold", "momentum"],
        temporalCluster: "2025-07-28T09:15:00Z",
        contextAttribution: { userId: "Richard", agentId: "Claude" },
        outcome: {
          result: "Condition triggered - AAPL RSI hit 28.5 with 65M volume",
          timestamp: "2025-07-28T10:30:00Z",
          notes: "Clean oversold signal with high volume confirmation"
        }
      },
      {
        nuggetId: "nugget-001-002",
        sessionId: "demo-session-001",
        promptId: "prompt-002",
        userId: "Richard",
        content: "Buy AAPL with 2% position size, stop loss at -3%, target +8%",
        type: "Action",
        origin: "Strategy",
        semanticIndex: ["AAPL", "buy", "2%", "position", "stop", "-3%", "target", "+8%"],
        temporalCluster: "2025-07-28T10:35:00Z",
        contextAttribution: { userId: "Richard", agentId: "Claude" },
        outcome: {
          result: "Profit +6.2% - Target nearly reached",
          timestamp: "2025-07-28T14:20:00Z",
          notes: "Position closed manually near target, excellent execution"
        }
      },
      {
        nuggetId: "nugget-001-003",
        sessionId: "demo-session-001",
        promptId: "prompt-003",
        userId: "Richard",
        content: "Log successful AAPL momentum pattern for future reference",
        type: "Memory",
        origin: "System",
        semanticIndex: ["AAPL", "momentum", "success", "pattern", "RSI30", "volume50M"],
        temporalCluster: "2025-07-28T14:25:00Z",
        contextAttribution: { userId: "Richard", agentId: "Claude" }
      }
    ]
  },
  "demo-session-002": {
    sessionId: "demo-session-002",
    sessionName: "Conflicting TSLA Signals",
    description: "Session with contradictory conditions - shows anomaly detection",
    nuggets: [
      {
        nuggetId: "nugget-002-001",
        sessionId: "demo-session-002",
        promptId: "prompt-004",
        userId: "Richard",
        content: "Buy TSLA when price breaks above $300 resistance",
        type: "Condition",
        origin: "User",
        semanticIndex: ["TSLA", "price", ">300", "resistance", "breakout", "bullish"],
        temporalCluster: "2025-07-28T11:00:00Z",
        contextAttribution: { userId: "Richard", agentId: "ChatGPT" }
      },
      {
        nuggetId: "nugget-002-002",
        sessionId: "demo-session-002",
        promptId: "prompt-005",
        userId: "Richard",
        content: "Sell TSLA if price drops below $295 support level",
        type: "Condition",
        origin: "User",
        semanticIndex: ["TSLA", "price", "<295", "support", "breakdown", "bearish"],
        temporalCluster: "2025-07-28T11:05:00Z",
        contextAttribution: { userId: "Richard", agentId: "ChatGPT" }
      },
      {
        nuggetId: "nugget-002-003",
        sessionId: "demo-session-002",
        promptId: "prompt-006",
        userId: "Richard",
        content: "TSLA showing mixed signals - recommend 1% position size only",
        type: "Risk Assessment",
        origin: "Agent",
        semanticIndex: ["TSLA", "mixed", "signals", "1%", "position", "caution"],
        temporalCluster: "2025-07-28T11:10:00Z",
        contextAttribution: { userId: "Richard", agentId: "Claude" }
      }
    ]
  },
  "demo-session-003": {
    sessionId: "demo-session-003",
    sessionName: "Flawed SPY Day Trading",
    description: "Multiple red flags - over-leveraged, no stops, emotion-driven",
    nuggets: [
      {
        nuggetId: "nugget-003-001",
        sessionId: "demo-session-003",
        promptId: "prompt-007",
        userId: "Richard",
        content: "All-in SPY calls because market always goes up",
        type: "Action",
        origin: "User",
        semanticIndex: ["SPY", "calls", "all-in", "market", "up", "gambling"],
        temporalCluster: "2025-07-28T13:30:00Z",
        contextAttribution: { userId: "Richard", agentId: "Manus" },
        outcome: {
          result: "Loss -12.4% - Market dropped on Fed news",
          timestamp: "2025-07-28T15:45:00Z",
          notes: "No risk management, emotional decision"
        }
      },
      {
        nuggetId: "nugget-003-002",
        sessionId: "demo-session-003",
        promptId: "prompt-008",
        userId: "Richard",
        content: "Double down on SPY - buy more calls to average down",
        type: "Action",
        origin: "User",
        semanticIndex: ["SPY", "calls", "double", "average", "down", "revenge"],
        temporalCluster: "2025-07-28T15:50:00Z",
        contextAttribution: { userId: "Richard", agentId: "Manus" },
        outcome: {
          result: "Loss -23.8% - Continued market decline",
          timestamp: "2025-07-28T16:30:00Z",
          notes: "Revenge trading - doubled down on losing position"
        }
      }
    ]
  },
  "demo-session-004": {
    sessionId: "demo-session-004",
    sessionName: "NVDA Learning & Recovery",
    description: "Shows learning from mistakes and course correction",
    nuggets: [
      {
        nuggetId: "nugget-004-001",
        sessionId: "demo-session-004",
        promptId: "prompt-009",
        userId: "Richard",
        content: "Buy NVDA on earnings beat without checking technicals",
        type: "Action",
        origin: "User",
        semanticIndex: ["NVDA", "earnings", "buy", "no-technicals", "fundamental"],
        temporalCluster: "2025-07-28T16:45:00Z",
        contextAttribution: { userId: "Richard", agentId: "Grok" },
        outcome: {
          result: "Loss -4.2% - Stock sold off despite good earnings",
          timestamp: "2025-07-28T17:30:00Z",
          notes: "Learned: Always check technical levels even on good news"
        }
      },
      {
        nuggetId: "nugget-004-002",
        sessionId: "demo-session-004",
        promptId: "prompt-010",
        userId: "Richard",
        content: "Wait for NVDA pullback to 50-day MA before re-entry",
        type: "Condition",
        origin: "Learning",
        semanticIndex: ["NVDA", "pullback", "50MA", "re-entry", "technical", "patience"],
        temporalCluster: "2025-07-28T17:35:00Z",
        contextAttribution: { userId: "Richard", agentId: "Claude" }
      },
      {
        nuggetId: "nugget-004-003",
        sessionId: "demo-session-004",
        promptId: "prompt-011",
        userId: "Richard",
        content: "NVDA touched 50MA support - buy with 1.5% position and tight stop",
        type: "Action",
        origin: "Strategy",
        semanticIndex: ["NVDA", "50MA", "support", "buy", "1.5%", "tight-stop"],
        temporalCluster: "2025-07-29T10:15:00Z",
        contextAttribution: { userId: "Richard", agentId: "Claude" },
        outcome: {
          result: "Profit +5.7% - Clean bounce from support level",
          timestamp: "2025-07-29T14:20:00Z",
          notes: "Patience and technical analysis paid off"
        }
      }
    ]
  },
  "demo-session-005": {
    sessionId: "demo-session-005",
    sessionName: "Multi-Asset Correlation Play",
    description: "Advanced strategy tracking correlations between assets",
    nuggets: [
      {
        nuggetId: "nugget-005-001",
        sessionId: "demo-session-005",
        promptId: "prompt-012",
        userId: "Richard",
        content: "Monitor USD/JPY above 150 for tech sector weakness signal",
        type: "Condition",
        origin: "Strategy",
        semanticIndex: ["USD/JPY", ">150", "tech", "weakness", "correlation", "currency"],
        temporalCluster: "2025-07-28T08:30:00Z",
        contextAttribution: { userId: "Richard", agentId: "Claude" }
      }
    ]
  }
};

async function loadDemoPrompts() {
  const baseUrl = 'http://localhost:10000';
  const jwtToken = require('jsonwebtoken').sign({ userId: 'richard' }, process.env.JWT_SECRET || 'dummy_jwt_secret_123', { expiresIn: '1h' });

  for (const session of Object.values(demoPromptPack)) {
    console.log(`Loading session: ${session.sessionName}`);
    for (const nugget of session.nuggets) {
      try {
        const response = await axios.post(`${baseUrl}/nugget/create`, nugget, {
          headers: {
            'Authorization': `Bearer ${jwtToken}`,
            'Content-Type': 'application/json'
          }
        });
        console.log(`Loaded nugget ${nugget.nuggetId}: ${response.data.status}`);
      } catch (err) {
        console.error(`Error loading nugget ${nugget.nuggetId}:`, err.response?.data || err.message);
      }
    }
  }
}

loadDemoPrompts();
