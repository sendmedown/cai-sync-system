import React, { useState, useEffect } from 'react';
import { useWebSocket } from './WebSocketContext'; // Custom hook for WebSocket
import 'tailwindcss/tailwind.css';

// Timeline Component inspired by MS Recall
const Timeline = ({ sessionId }) => {
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const ws = useWebSocket();

  useEffect(() => {
    if (ws) {
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'prompt_processed') {
          setBreadcrumbs((prev) => [...prev, { promptId: data.promptId, content: data.content, timestamp: data.timestamp }]);
        }
      };
    }
  }, [ws]);

  return (
    <div className="p-4 bg-gray-100 rounded-lg shadow-md">
      <h2 className="text-lg font-bold mb-2">Session Timeline</h2>
      <div className="relative">
        <div className="absolute h-full w-1 bg-blue-500 left-4"></div>
        {breadcrumbs.map((crumb, index) => (
          <div key={index} className="mb-4 flex items-center">
            <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
            <div className="ml-4 p-2 bg-white rounded-lg shadow">
              <p className="text-sm font-semibold">{crumb.promptId}</p>
              <p className="text-xs text-gray-600">{crumb.content}</p>
              <p className="text-xs text-gray-400">{new Date(crumb.timestamp).toLocaleString()}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Memory Map Component (KM Nugget Navigator)
const KMNuggetNavigator = ({ sessionId }) => {
  const [nuggets, setNuggets] = useState([]);

  useEffect(() => {
    fetch(`https://bioquantum-api.onrender.com/session/${sessionId}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
      .then((res) => res.json())
      .then((data) => setNuggets(data.breadcrumbs || []));
  }, [sessionId]);

  return (
    <div className="p-4 bg-gray-100 rounded-lg shadow-md">
      <h2 className="text-lg font-bold mb-2">KM Nugget Navigator</h2>
      <div className="grid grid-cols-3 gap-4">
        {nuggets.map((nugget, index) => (
          <div key={index} className="p-2 bg-white rounded-lg shadow hover:bg-blue-100 cursor-pointer">
            <p className="text-sm font-semibold">{nugget.promptId}</p>
            <p className="text-xs text-gray-600 truncate">{nugget.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export { Timeline, KMNuggetNavigator };