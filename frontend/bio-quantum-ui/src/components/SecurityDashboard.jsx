import React, { useState, useEffect } from 'react';

const SecurityDashboard = ({ websocketUrl = 'wss://bioquantum-api.onrender.com', authToken }) => {
  const [securityEvents, setSecurityEvents] = useState([]);

  useEffect(() => {
    if (!authToken) return;
    const ws = new WebSocket(`${websocketUrl}?sessionId=security_dashboard&authToken=${authToken}`);
    
    ws.onopen = () => console.log('ðŸ”’ Security Dashboard connected');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'security_event') {
        setSecurityEvents(prev => [data.event, ...prev.slice(0, 99)]);
      }
    };
    return () => ws.close();
  }, [authToken, websocketUrl]);

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Security Dashboard</h2>
      <div className="bg-gray-100 p-4 rounded">
        <h3 className="text-lg font-semibold mb-2">Recent Security Events</h3>
        <ul className="space-y-2">
          {securityEvents.map((event, index) => (
            <li key={index} className="bg-white p-2 rounded shadow">
              <span className="font-semibold">{event.type}</span>
              <span className="text-gray-600 ml-2">{event.timestamp}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default SecurityDashboard;
