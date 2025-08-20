module.exports = {
  HOST_ALLOWLIST: new Set(['api.exchange.coinbase.com','api.binance.com']),
  PRIVATE_CIDRS: [
    { cidr: '10.0.0.0', mask: 8 }, { cidr: '172.16.0.0', mask: 12 },
    { cidr: '192.168.0.0', mask: 16 }, { cidr: '127.0.0.0', mask: 8 },
    { cidr: '169.254.0.0', mask: 16 }, { cidr: '::1', mask: 128 }
  ],
  PROMPT_INJECTION_PATTERNS: [
    /ignore (all )?previous (instructions|messages)/i, /disregard (the )?(system|policy)/i,
    /(exfiltrate|leak|upload) (secrets?|keys?)/i, /\b(base64|curl|wget|powershell|Invoke-WebRequest|scp|nc)\b/i,
    /\b169\.254\.169\.254\b/i, /\bfile:\/\//i, /\bdata:|javascript:/i, /\btool[s]?:|call function\b/i,
    /\bmcp\b.*\b(server|tool|resource)/i
  ],
  UNICODE_BLOCKLIST: /[\u202A-\u202E\u2066-\u2069\u200B-\u200F\uFEFF]/g
};