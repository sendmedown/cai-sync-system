import React, { useState, useEffect } from 'react';
import ReactFlow, { Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import { v4 as uuidv4 } from 'uuid';

const StrategyMemoryMap = ({ websocketUrl = 'wss://bioquantum-api.onrender.com', authToken }) => {
  const [nuggets, setNuggets] = useState([]);
  const [codonTraces, setCodonTraces] = useState([]);
  const [mutationReplayEvents, setMutationReplayEvents] = useState([]);
  const [replayIndex, setReplayIndex] = useState(0);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [semanticMap, setSemanticMap] = useState({ nodes: [], edges: [] });
  const [nuggetNarratives, setNuggetNarratives] = useState({});

  useEffect(() => {
    if (!authToken) return;
    const ws = new WebSocket(`${websocketUrl}?sessionId=strategy_map_${uuidv4()}&authToken=${authToken}`);
    
    ws.onopen = () => console.log('ðŸ§¬ Strategy Memory Map connected');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'nugget_update') {
        setNuggets(prev => [data, ...prev].slice(0, 100));
      } else if (data.type === 'codon_trace') {
        setCodonTraces(prev => [data, ...prev].slice(0, 50));
      } else if (data.type === 'mutation_replay') {
        setMutationReplayEvents(data.events);
      }
    };
    ws.onerror = (error) => console.error('âŒ WebSocket error:', error);
    return () => ws.close();
  }, [authToken, websocketUrl]);

  useEffect(() => {
    // Fetch semanticZoomMap.json
    fetch('/shared/phase4_mutation_replay_bundle/semanticZoomMap.json')
      .then(res => res.json())
      .then(data => setSemanticMap({
        nodes: data.nodes.map(node => ({
          id: node.id,
          data: { label: node.label, tooltip: nuggetNarratives[node.id] || 'No narrative' },
          position: node.position
        })),
        edges: data.edges
      }))
      .catch(err => {
        console.error('âŒ Failed to load semanticZoomMap.json:', err);
        // Mock data fallback
        setSemanticMap({
          nodes: [
            { id: 'session_1', data: { label: 'Session 1', tooltip: 'Session root' }, position: { x: 0, y: 0 } },
            { id: 'nugget_1', data: { label: 'Nugget 1', tooltip: 'Market analysis' }, position: { x: 100, y: 100 } },
            { id: 'codon_1', data: { label: 'Codon 1', tooltip: 'Strategy codon' }, position: { x: 200, y: 200 } }
          ],
          edges: [
            { id: 'e1', source: 'session_1', target: 'nugget_1' },
            { id: 'e2', source: 'nugget_1', target: 'codon_1' }
          ]
        });
      });

    // Fetch nuggetNarratives.json
    fetch('/shared/phase4_mutation_replay_bundle/nuggetNarratives.json')
      .then(res => res.json())
      .then(setNuggetNarratives)
      .catch(err => {
        console.error('âŒ Failed to load nuggetNarratives.json:', err);
        setNuggetNarratives({
          'nugget_1': 'This nugget represents a market analysis strategy with high confidence.',
          'codon_1': 'Codon for automated trading logic, mutation-free.'
        });
      });
  }, []);

  const handleReplaySlider = (e) => {
    setReplayIndex(parseInt(e.target.value));
  };

  const zoomIn = () => setZoomLevel(prev => Math.min(prev + 0.2, 3));
  const zoomOut = () => setZoomLevel(prev => Math.max(prev - 0.2, 0.5));

  const currentReplayEvent = mutationReplayEvents[replayIndex] || {};

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Strategy Memory Map</h2>
      <div style={{ height: '500px', width: '100%', border: '1px solid #ccc' }}>
        <ReactFlow
          nodes={semanticMap.nodes}
          edges={semanticMap.edges}
          fitView
          style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.3s' }}
          nodesDraggable={false}
        >
          <Controls />
        </ReactFlow>
      </div>
      <div className="mt-4">
        <button className="bg-blue-500 text-white px-4 py-2 rounded mr-2" onClick={zoomIn}>Zoom In</button>
        <button className="bg-blue-500 text-white px-4 py-2 rounded" onClick={zoomOut}>Zoom Out</button>
      </div>
      <div className="mt-4">
        <h3 className="text-lg font-semibold">Mutation Replay</h3>
        <input
          type="range"
          min={0}
          max={mutationReplayEvents.length - 1}
          value={replayIndex}
          onChange={handleReplaySlider}
          className="w-full"
        />
        <p>Current Event: {JSON.stringify(currentReplayEvent)}</p>
      </div>
      <div className="mt-4">
        <h3 className="text-lg font-semibold">Recent Nuggets</h3>
        <ul className="list-disc pl-5">
          {nuggets.map(nugget => (
            <li key={nugget.nuggetId} title={nuggetNarratives[nugget.nuggetId] || 'No narrative'}>
              {nugget.content} (ID: {nugget.nuggetId}, Session: {nugget.sessionId})
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-4">
        <h3 className="text-lg font-semibold">Codon Traces</h3>
        <ul className="list-disc pl-5">
          {codonTraces.map(trace => (
            <li key={trace.requestId}>
              {trace.sequence} (Score: {trace.degScore})
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default StrategyMemoryMap;
