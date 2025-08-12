import React, { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';

const ChatBot = ({ apiUrl = 'https://bioquantum-api.onrender.com', authToken }) => {
  const [message, setMessage] = useState('');
  const [responses, setResponses] = useState([]);

  const sendMessage = async () => {
    if (!message) return;
    
    try {
      const response = await fetch(`${apiUrl}/nugget/create`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          userId: 'chatbot_user',
          content: message,
          promptId: `prompt_${uuidv4()}`,
          context: { sessionId: `session_${uuidv4()}` }
        })
      });
      
      const data = await response.json();
      setResponses(prev => [...prev, { message, response: data }].slice(-50));
      setMessage('');
    } catch (error) {
      console.error('âŒ ChatBot error:', error);
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">AI Trading ChatBot</h2>
      <div className="mb-4">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Enter trading prompt"
          className="w-full p-2 border rounded"
        />
        <button 
          onClick={sendMessage}
          className="mt-2 bg-blue-500 text-white px-4 py-2 rounded"
        >
          Send
        </button>
      </div>
      <div>
        <h3 className="text-lg font-semibold mb-2">Responses</h3>
        <ul className="space-y-2">
          {responses.map((res, index) => (
            <li key={index} className="bg-gray-100 p-2 rounded">
              <div className="font-semibold">Prompt: {res.message}</div>
              <div className="text-gray-600">Response: {JSON.stringify(res.response)}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default ChatBot;
