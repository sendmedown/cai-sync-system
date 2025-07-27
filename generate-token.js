const jwt = require('jsonwebtoken');

const token = jwt.sign(
  { userId: 'Richard' },
  'dummy_jwt_secret_123',  // This must match your backend
  { expiresIn: '1h' }
);

console.log("Your valid JWT token:\n\n" + token);
