import React, { useState, useEffect } from 'react';
import { Sparklines, SparklinesLine } from 'react-sparklines';

const AgentStressDashboard = ({ apiUrl = 'https://bioquantum-api.onrender.com', websocketUrl = 'wss://bioquantum-api.onrender.com', authToken }) => {
  const [metrics, setMetrics] = useState({
    jwtFailures: { value: 0, history: [] },
    replayAttacks: { value: 0, history: [] },
    codonMutationRate: { value: 0, history: [] },
    memoryCorrectionSuccess: { value: 0, history: [] },
    topCodonDrift: 'N/A',
    memoryRepairs: 0
  });
  const [isDebugOpen, setIsDebugOpen] = useState(false);

  useEffect(() => {
    // WebSocket for live metrics
    const ws = new WebSocket(`${websocketUrl}/metrics/ws?token=${authToken}`);
    ws.onopen = () => console.log('ðŸ›¡ï¸ Agent Stress Dashboard WebSocket connected');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'metrics_update') {
        setMetrics(prev => ({
          jwtFailures: { value: data.jwtFailures, history: [...prev.jwtFailures.history, data.jwtFailures].slice(-50) },
          replayAttacks: { value: data.replayAttacks, history: [...prev.replayAttacks.history, data.replayAttacks].slice(-50) },
          codonMutationRate: { value: data.codonMutationRate, history: [...prev.codonMutationRate.history, data.codonMutationRate].slice(-50) },
          memoryCorrectionSuccess: { value: data.memoryCorrectionSuccess, history: [...prev.memoryCorrectionSuccess.history, data.memoryCorrectionSuccess].slice(-50) },
          topCodonDrift: data.topCodonDrift || 'N/A',
          memoryRepairs: data.memoryRepairs || 0
        }));
      }
    };
    ws.onerror = (error) => console.error('âŒ WebSocket error:', error);
    ws.onclose = () => console.log('WebSocket closed');

    // Fallback polling if WebSocket fails
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${apiUrl}/metrics`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        setMetrics(prev => ({
          jwtFailures: { value: data.jwtFailures, history: [...prev.jwtFailures.history, data.jwtFailures].slice(-50) },
          replayAttacks: { value: data.replayAttacks, history: [...prev.replayAttacks.history, data.replayAttacks].slice(-50) },
          codonMutationRate: { value: data.codonMutationRate, history: [...prev.codonMutationRate.history, data.codonMutationRate].slice(-50) },
          memoryCorrectionSuccess: { value: data.memoryCorrectionSuccess, history: [...prev.memoryCorrectionSuccess.history, data.memoryCorrectionSuccess].slice(-50) },
          topCodonDrift: data.topCodonDrift || 'N/A',
          memoryRepairs: data.memoryRepairs || 0
        }));
      } catch (error) {
        console.error('âŒ Metrics fetch error:', error);
      }
    }, 5000);

    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, [apiUrl, websocketUrl, authToken]);

  const getBadgeStyle = (value, threshold) => ({
    color: value > threshold ? '#dc2626' : '#15803d',
    backgroundColor: value > threshold ? '#fee2e2' : '#dcfce7',
    padding: '4px 8px',
    borderRadius: '4px'
  });

  return (
    <div className="p-4 bg-gray-100 rounded-lg">
      <h2 className="text-2xl font-bold mb-4">Agent Stress Dashboard</h2>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h3 style={getBadgeStyle(metrics.jwtFailures.value, 5)}>
            JWT Failures: {metrics.jwtFailures.value}
            {metrics.jwtFailures.value > 10 && <span className="ml-2 bg-red-600 text-white px-2 py-1 rounded">High</span>}
          </h3>
          <Sparklines data={metrics.jwtFailures.history} width={100} height={20}>
            <SparklinesLine color={metrics.jwtFailures.value > 5 ? 'red' : 'green'} />
          </Sparklines>
        </div>
        <div>
          <h3 style={getBadgeStyle(metrics.replayAttacks.value, 5)}>
            Replay Attacks: {metrics.replayAttacks.value}
            {metrics.replayAttacks.value > 10 && <span className="ml-2 bg-red-600 text-white px-2 py-1 rounded">High</span>}
          </h3>
          <Sparklines data={metrics.replayAttacks.history} width={100} height={20}>
            <SparklinesLine color={metrics.replayAttacks.value > 5 ? 'red' : 'green'} />
          </Sparklines>
        </div>
        <div>
          <h3 style={getBadgeStyle(metrics.codonMutationRate.value, 20)}>
            Codon Mutation Rate: {metrics.codonMutationRate.value.toFixed(2)}%
            {metrics.codonMutationRate.value > 30 && <span className="ml-2 bg-red-600 text-white px-2 py-1 rounded">High</span>}
          </h3>
          <Sparklines data={metrics.codonMutationRate.history} width={100} height={20}>
            <SparklinesLine color={metrics.codonMutationRate.value > 20 ? 'red' : 'green'} />
          </Sparklines>
        </div>
        <div>
          <h3 style={getBadgeStyle(100 - metrics.memoryCorrectionSuccess.value, 10)}>
            Memory Correction Success: {metrics.memoryCorrectionSuccess.value.toFixed(2)}%
            {metrics.memoryCorrectionSuccess.value < 90 && <span className="ml-2 bg-red-600 text-white px-2 py-1 rounded">Low</span>}
          </h3>
          <Sparklines data={metrics.memoryCorrectionSuccess.history} width={100} height={20}>
            <SparklinesLine color={metrics.memoryCorrectionSuccess.value < 90 ? 'red' : 'green'} />
          </Sparklines>
        </div>
      </div>
      <div className="mt-4">
        <button
          className="bg-blue-500 text-white px-4 py-2 rounded"
          onClick={() => setIsDebugOpen(!isDebugOpen)}
        >
          {isDebugOpen ? 'Hide' : 'Show'} Codon Debug Info
        </button>
        {isDebugOpen && (
          <div className="mt-2 p-4 bg-gray-200 rounded">
            <h4>Dominant Mutation: {metrics.topCodonDrift}</h4>
            <h4>Repair Attempts: {metrics.memoryRepairs}</h4>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentStressDashboard;
