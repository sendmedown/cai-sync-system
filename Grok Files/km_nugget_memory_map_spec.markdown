# KM Nugget Memory Map UI Specification

## Overview
The KM Nugget Memory Map UI is a dynamic visualization layer for the Bio-Quantum AI Trading Platform, enabling users to explore KM Nuggets (insights, decisions, data snippets) via an interactive graph, timeline, and agent activity panel. It integrates with `apiBridge.js` (WebSocket, REST) and supports Phase 9’s Autonomous Enterprise Intelligence Layer.

## Components
### 1. Interactive Memory Graph
- **Function**: Display KM Nuggets as nodes, contextual links as edges.
- **Features**:
  - Hover: Show summary, provenance (source, agent, timestamp).
  - Click: Show full detail, edit form, prompt preview.
  - Tooltip: Recent interactions, update history.
- **Tech**: ReactFlow for graph rendering, Tailwind CSS for styling.
- **Data**: Fetch from `/session/:sessionId` (breadcrumbs), `/hldd` (schema).

### 2. Layer Control Sidebar
- **Function**: Toggle visualization layers and filters.
- **Features**:
  - Layers: Chronological, Topic Clusters, Agent Attribution, User vs AI.
  - Filters: Author, Time, Use-case (Strategy Builder, Risk Engine).
- **Tech**: React, Tailwind CSS, Zustand for state management.
- **Data**: Query `/agent/route` for agent metadata.

### 3. Temporal Timeline Strip
- **Function**: Scrollable timeline of KM Nugget creation/usage.
- **Features**:
  - Highlights: Creation, usage events.
  - Click: Jump to corresponding graph node.
- **Tech**: ReactFlow Timeline, WebSocket for real-time updates.
- **Data**: Subscribe to WebSocket `chat_prompt` events.

### 4. Agent Activity Panel
- **Function**: Track AI agent interactions with KM Nuggets.
- **Features**:
  - List: Agent ID, prompt chain, fallback triggers.
  - Replay: Sequence playback (future).
- **Tech**: React, Tailwind CSS.
- **Data**: Fetch from `/agent/route`, `/session/:sessionId`.

### 5. Semantic Zoom
- **Function**: Zoom between high-level clusters and individual nuggets.
- **Features**:
  - Zoom Out: Clusters (patents, trades, risks).
  - Zoom In: Nugget → Prompt → Action.
- **Tech**: ReactFlow zoom controls, t-SNE clustering for layout.
- **Data**: Vector embeddings from Memory Engine (future).

## Implementation
### Backend (`apiBridge.js`, ID: `60b814e4-b0d9-4963-94f4-8effe5454caa`)
- **Endpoints**:
  - `/nugget/create`: Create KM Nugget (POST, JWT-protected).
  - `/nugget/query`: Query nuggets by filter (POST, JWT-protected).
- **WebSocket**: Push `nugget_update` events for real-time graph updates.
- **Update**:
  ```javascript
  app.post('/nugget/create', (req, res) => {
      const { userId, content, promptId, context } = req.body;
      const token = req.headers.authorization?.split(' ')[1];
      try {
          jwt.verify(token, process.env.JWT_SECRET || 'dummy_jwt_secret_123');
          const nuggetId = uuidv4();
          const sessionId = context.sessionId || uuidv4();
          sessionBreadcrumbs.set(sessionId, [...(sessionBreadcrumbs.get(sessionId) || []), { nuggetId, content, promptId, timestamp: new Date().toISOString() }]);
          wss.clients.forEach(client => {
              if (client.sessionId === sessionId) {
                  client.send(JSON.stringify({ type: 'nugget_update', nuggetId, content, promptId, requestId: uuidv4() }));
              }
          });
          res.status(200).json({ status: 'success', nuggetId, sessionId, requestId: uuidv4() });
      } catch (err) {
          res.status(401).json({ error: 'Invalid JWT', requestId: uuidv4() });
      }
  });
  app.post('/nugget/query', (req, res) => {
      const { filters } = req.body; // { author, timeRange, useCase }
      const token = req.headers.authorization?.split(' ')[1];
      try {
          jwt.verify(token, process.env.JWT_SECRET || 'dummy_jwt_secret_123');
          const nuggets = Array.from(sessionBreadcrumbs.values()).flat().filter(n => {
              // Mock filtering logic
              return filters.author ? n.userId === filters.author : true;
          });
          res.status(200).json({ nuggets, requestId: uuidv4() });
      } catch (err) {
          res.status(401).json({ error: 'Invalid JWT', requestId: uuidv4() });
      }
  });
  ```
- **Deploy**:
  ```bash
  git add apiBridge.js
  git commit -m "Add /nugget/create, /nugget/query for KM Nugget UI"
  git push origin deploy-clean
  ```

### Frontend (`km_nugget_memory_map.jsx`)
- **Structure**:
  - `MemoryGraph`: ReactFlow graph with nodes/edges.
  - `LayerControl`: Sidebar with toggle buttons, filters.
  - `TimelineStrip`: Scrollable timeline component.
  - `AgentActivity`: List of agent interactions.
- **Tech**: ReactFlow, Tailwind CSS, Zustand, WebSocket hook.
- **Example**:
  ```jsx
  import React, { useState, useEffect } from 'react';
  import ReactFlow, { Controls } from 'react-flow-renderer';
  import { useWebSocket } from './WebSocketContext';
  import 'tailwindcss/tailwind.css';

  const KMNuggetMemoryMap = ({ sessionId }) => {
      const [nodes, setNodes] = useState([]);
      const [edges, setEdges] = useState([]);
      const ws = useWebSocket();

      useEffect(() => {
          fetch(`https://bioquantum-api.onrender.com/session/${sessionId}`, {
              headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
          })
              .then(res => res.json())
              .then(data => {
                  const newNodes = data.breadcrumbs.map((crumb, i) => ({
                      id: crumb.nuggetId,
                      data: { label: crumb.content, promptId: crumb.promptId },
                      position: { x: i * 100, y: i * 50 }
                  }));
                  const newEdges = data.breadcrumbs.slice(1).map((crumb, i) => ({
                      id: `e${i}`,
                      source: data.breadcrumbs[i].nuggetId,
                      target: crumb.nuggetId
                  }));
                  setNodes(newNodes);
                  setEdges(newEdges);
              });
          if (ws) {
              ws.onmessage = (event) => {
                  const data = JSON.parse(event.data);
                  if (data.type === 'nugget_update') {
                      setNodes(prev => [...prev, {
                          id: data.nuggetId,
                          data: { label: data.content, promptId: data.promptId },
                          position: { x: prev.length * 100, y: prev.length * 50 }
                      }]);
                      if (prev.length > 0) {
                          setEdges(prev => [...prev, {
                              id: `e${prev.length}`,
                              source: prev[prev.length - 1].id,
                              target: data.nuggetId
                          }]);
                      }
                  }
              };
          }
      }, [ws, sessionId]);

      return (
          <div className="h-screen flex">
              <div className="w-3/4">
                  <ReactFlow nodes={nodes} edges={edges}>
                      <Controls />
                  </ReactFlow>
              </div>
              <div className="w-1/4 p-4 bg-gray-100">
                  <h2 className="text-lg font-bold">Layer Control</h2>
                  {/* Add toggles and filters */}
              </div>
          </div>
      );
  };

  export default KMNuggetMemoryMap;
  ```

### Tasks
- **Grok**: Implement `/nugget/create`, `/nugget/query` in `apiBridge.js`; draft `km_nugget_memory_map.jsx`.
- **Claude**: Validate prompt chain integration with KM Nuggets; map MS Recall SPI to memory graph.
- **Manus**: Create wireframes for Memory Graph, Timeline Strip, Agent Activity Panel.

### Deliverables
- **Grok**: Updated `apiBridge.js`, `km_nugget_memory_map.jsx` (July 26, 12:00 PM EDT).
- **Claude**: `spi_mapping_report.md` with KM Nugget UI recommendations (July 26, 8:00 AM EDT).
- **Manus**: `km_nugget_wireframes.png` (July 26, 8:00 AM EDT).

### Timeline
- July 26, 8:00 AM EDT: Claude/Manus deliverables, YouTube video preview.
- July 26, 12:00 PM EDT: Grok deliverables, PDF snapshot.