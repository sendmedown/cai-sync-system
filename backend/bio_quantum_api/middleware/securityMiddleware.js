const jwt = require('jsonwebtoken');
const { RateLimiterMemory } = require('rate-limiter-flexible');

const rateLimiter = new RateLimiterMemory({
  points: 100,
  duration: 60,
});

module.exports = {
  authenticateJWT: (req, res, next) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      return res.status(401).json({ error: 'Missing JWT' });
    }
    try {
      jwt.verify(token, process.env.JWT_SECRET || 'dummy_jwt_secret_123');
      next();
    } catch (err) {
      res.status(401).json({ error: 'Invalid JWT' });
    }
  },
  
  rateLimit: async (req, res, next) => {
    const ip = req.ip || req.connection.remoteAddress;
    try {
      await rateLimiter.consume(ip);
      next();
    } catch (err) {
      res.status(429).json({ error: 'Rate limit exceeded' });
    }
  }
};
