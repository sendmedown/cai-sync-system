```jsx
import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import './Dashboard.css'; // Assumed CSS for tooltip alignment

const AIPopup = ({ recommendation, onClose }) => (
  <motion.div
    initial={{ opacity: 0, y: -20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    transition={{ duration: 0.4 }}
    style={{
      position: 'absolute',
      top: '20px',
      right: '20px',
      background: '#F0F4F8',
      padding: '15px',
      borderRadius: '8px',
      boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
      zIndex: 1000,
    }}
  >
    <p>
      <strong>{recommendation.action} {recommendation.ticker}</strong> at ${recommendation.price} (
      {recommendation.confidence})<br />
      {recommendation.portfolioImpact}
    </p>
    <button
      onClick={onClose}
      style={{ background: '#FF6B6B', color: 'white', padding: '5px 10px', border: 'none', borderRadius: '5px' }}
    >
      Close
    </button>
  </motion.div>
);

const Dashboard = () => {
  const [priceData, setPriceData] = useState([]);
  const [recommendation, setRecommendation] = useState(null);

  useEffect(() => {
    axios
      .get('/api/market/ticker/AAPL')
      .then((response) => setPriceData(response.data.prices))
      .catch((error) => console.error('Market API Error:', error));
  }, []);

  const chartData = {
    labels: priceData.map((d) => d.time),
    datasets: [
      {
        label: 'Portfolio Value (47% Returns)',
        data: priceData.map((d) => d.close * 1.47),
        borderColor: '#00C4B4',
        backgroundColor: 'rgba(0, 196, 180, 0.2)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const handleRecommendation = async () => {
    try {
      const response = await axios.post('/api/bridge/simulate-ai', {
        agent: 'Grok_4',
        priceData,
      });
      setRecommendation(response.data);
    } catch (error) {
      console.error('Bridge API Error:', error);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6 }}
      style={{
        padding: '20px',
        maxWidth: '1200px',
        margin: 'auto',
        background: '#fff',
        borderRadius: '10px',
        display: 'grid',
        gridTemplateColumns: '3fr 1fr',
        gap: '20px',
      }}
    >
      <div>
        <h2>Bio-Quantum AI Trading Dashboard</h2>
        <motion.div
          initial={{ y: 20 }}
          animate={{ y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Line
            data={chartData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { position: 'top' },
                tooltip: {
                  backgroundColor: '#00C4B4',
                  titleColor: '#fff',
                  bodyColor: '#fff',
                  borderColor: '#008080',
                  borderWidth: 1,
                  position: 'nearest',
                  callbacks: {
                    label: (context) => `$${context.parsed.y.toFixed(2)}`,
                  },
                },
              },
            }}
            height={400}
          />
        </motion.div>
      </div>
      <div>
        <motion.button
          whileHover={{ scale: 1.1, backgroundColor: '#008080' }}
          whileTap={{ scale: 0.9 }}
          onClick={handleRecommendation}
          style={{
            background: '#00C4B4',
            color: 'white',
            padding: '12px 24px',
            border: 'none',
            borderRadius: '8px',
            width: '100%',
            cursor: 'pointer',
          }}
        >
          Get AI Recommendation
        </motion.button>
        <AnimatePresence>
          {recommendation && <AIPopup recommendation={recommendation} onClose={() => setRecommendation(null)} />}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default Dashboard;
```