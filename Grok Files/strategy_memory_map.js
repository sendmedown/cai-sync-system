import React, { useState, useEffect } from 'react';
import ReactFlow, { Controls, Background } from 'react-flow-renderer';
import { useWebSocket } from './WebSocketContext'; // Custom hook for WebSocket
import 'tailwindcss/tailwind.css';

// Custom Node Component for Conditions/Actions
const CustomNode = ({ data }) => {
  return (
    <div className="p-2 bg-white border-2 border-blue-500 rounded-lg shadow-md w-40">
      <p className="text-sm font-semibold">{data.label}</p>
      <p className="text-xs text-gray-600">{data.type}: {data.promptId}</p>
      <p className="text-xs text-gray-400">{new Date(data.timestamp).toLocaleString()}</p>
      {data.outcome && (
        <p className="text-xs text-green-500">P/L: {data.outcome.pl} ({data.outcome.confidence}%)</p>
      )}
    </div>
  );
};

// Strategy Memory Map Component
const StrategyMemoryMap = ({ sessionId }) => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const ws = useWebSocket();

  // Fetch initial decision tree and KM Nuggets
  useEffect(() => {
    fetch(`https://bioquantum-api.onrender.com/session/${sessionId}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
      .then((res) => res.json())
      .then((data) => {
        const nuggets = data.breadcrumbs || [];
        const newNodes = nuggets.map((nugget, i) => ({
          id: nugget.nuggetId,
          type: 'custom',
          data: {
            label: nugget.content,
            type: nugget.type || 'Condition',
            promptId: nugget.promptId,
            timestamp: nugget.timestamp,
            outcome: nugget.outcome
          },
          position: { x: i * 150, y: i * 100 }
        }));
        const newEdges = nuggets.slice(1).map((nugget, i) => ({
          id: `e${i}`,
          source: nuggets[i].nuggetId,
          target: nugget.nuggetId,
          label: nugget.metadata?.operator || 'AND',
          animated: true
        }));
        setNodes(newNodes);
        setEdges(newEdges);
      });

    fetch(`https://bioquantum-api.onrender.com/nugget/query`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      method: 'POST',
      body: JSON.stringify({ filters: { useCase: 'strategy' } })
    })
      .then((res) => res.json())
      .then((data) => {
        // Merge additional nuggets if needed
      });
  }, [sessionId]);

  // Subscribe to WebSocket for real-time updates
  useEffect(() => {
    if (ws) {
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'nugget_update') {
          setNodes((prev) => [
            ...prev,
            {
              id: data.nuggetId,
              type: 'custom',
              data: {
                label: data.content,
                type: data.metadata?.type || 'Condition',
                promptId: data.promptId,
                timestamp: new Date().toISOString()
              },
              position: { x: prev.length * 150, y: prev.length * 100 }
            }
          ]);
          if (prev.length > 0) {
            setEdges((prev) => [
              ...prev,
              {
                id: `e${prev.length}`,
                source: prev[prev.length - 1].id,
                target: data.nuggetId,
                label: data.metadata?.operator || 'AND',
                animated: true
              }
            ]);
          }
        }
      };
    }
  }, [ws, nodes]);

  const nodeTypes = { custom: CustomNode };

  return (
    <div className="h-screen flex">
      <div className="w-3/4">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <div className="w-1/4 p-4 bg-gray-100">
        <h2 className="text-lg font-bold mb-2">Strategy Controls</h2>
        <button className="mb-2 p-2 bg-blue-500 text-white rounded">Simulate Strategy</button>
        <button className="mb-2 p-2 bg-green-500 text-white rounded">Execute Live</button>
        <h3 className="text-md font-semibold mt-4">Filters</h3>
        <select className="p-2 border rounded w-full">
          <option>Chronological</option>
          <option>Topic Clusters</option>
          <option>Agent Attribution</option>
        </select>
      </div>
    </div>
  );
};

export default StrategyMemoryMap;