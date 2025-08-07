```jsx
import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import './Dashboard.css';

const AIPopup = ({ recommendation, onClose }) => (
  <motion.div
    initial={{ opacity: 0, y: -20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    transition={{ duration: 0.4 }}
    className="ai-popup"
  >
    <p>
      <strong>{recommendation.action} {recommendation.ticker}</strong> at ${recommendation.price} ({recommendation.confidence})<br />
      {recommendation.portfolioImpact}
    </p>
    <button onClick={onClose} className="ai-popup-close">
      Close
    </button>
  </motion.div>
);

const Dashboard = () => {
  const [priceData, setPriceData] = useState([]);
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    setLoading(true);
    axios
      .get('/api/market/ticker/AAPL')
      .then((response) => setPriceData(response.data.prices))
      .catch((error) => console.error('Market API Error:', error))
      .finally(() => setLoading(false));
  }, []);

  const chartData = {
    labels: priceData.map((d) => d.time),
    datasets: [
      {
        label: 'Portfolio Value (47% Returns)',
        data: priceData.map((d) => d.close * 1.47),
        borderColor: isDarkMode ? '#4FD1C5' : '#00C4B4',
        backgroundColor: isDarkMode ? 'rgba(79, 209, 197, 0.2)' : 'rgba(0, 196, 180, 0.2)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const handleRecommendation = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/bridge/simulate-ai', {
        agent: 'Grok_4',
        priceData,
      });
      setRecommendation(response.data);
    } catch (error) {
      console.error('Bridge API Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6 }}
      className={`dashboard ${isDarkMode ? 'dark-mode' : ''}`}
    >
      <div className="dashboard-header">
        <h2>Bio-Quantum AI Trading Dashboard</h2>
        <button
          onClick={() => setIsDarkMode(!isDarkMode)}
          className="dark-mode-toggle"
        >
          {isDarkMode ? 'Light Mode' : 'Dark Mode'}
        </button>
      </div>
      {loading && (
        <motion.div
          className="spinner"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity }}
        />
      )}
      <div className="dashboard-content">
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
                  enabled: true,
                  position: 'nearest',
                  backgroundColor: isDarkMode ? '#2D3748' : '#00C4B4',
                  titleColor: '#fff',
                  bodyColor: '#fff',
                  borderColor: isDarkMode ? '#4A5568' : '#008080',
                  borderWidth: 1,
                  callbacks: {
                    label: (context) => `$${context.parsed.y.toFixed(2)}`,
                  },
                },
              },
            }}
            height={400}
          />
        </motion.div>
        <div className="dashboard-actions">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={handleRecommendation}
            className="recommendation-button"
            disabled={loading}
          >
            Get AI Recommendation
          </motion.button>
          <AnimatePresence>
            {recommendation && <AIPopup recommendation={recommendation} onClose={() => setRecommendation(null)} />}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
};

export default Dashboard;
```