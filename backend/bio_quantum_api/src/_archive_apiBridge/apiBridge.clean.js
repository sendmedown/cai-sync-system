const path = require("path");
const dotenv = require("dotenv");

// Load .env deterministically (root first, then backend override)
dotenv.config({ path: path.resolve(__dirname, "../../../.env") });
dotenv.config({ path: path.resolve(__dirname, "../.env") });

const express = require("express");
const cors = require("cors");
const jwt = require("jsonwebtoken");
const fs = require("fs");
const WebSocket = require("ws");

// ---- ENV ----
var MODE = (process.env.SECURITY_MODE || "strict").toLowerCase(); // "strict" | "dev"
var PORT_HTTP = parseInt(process.env.PORT_HTTP || "10000", 10);
var PORT_WS   = parseInt(process.env.PORT_WS   || "5003", 10);
var JWT_SECRET = process.env.JWT_SECRET || "dev_only_secret_change_me";
var JWT_ISSUER = process.env.JWT_ISSUER || "bio-quantum";
var TOKEN_TTL_SECONDS = parseInt(process.env.TOKEN_TTL_SECONDS || "3600", 10);
var ALLOWED = (process.env.ALLOWED_ORIGINS || "").split(",").map(function(s){return s.trim();}).filter(Boolean);
var dumpPath = "C:\\CAI-Sync-System\\bio-quantum-trading-platform-clean\\claude_dump.txt";

// ---- CORS ----
var corsOptions = {
  origin: function(origin, cb) {
    if (!origin || ALLOWED.length === 0 || ALLOWED.indexOf(origin) >= 0) return cb(null, true);
    return cb(new Error("CORS blocked"), false);
  }
};

// ---- Agent keys ----
function parseAgentKeys() {
  var raw = process.env.AGENT_API_KEYS || "";
  var map = new Map();
  raw.split(",").map(function(s){return s.trim();}).filter(Boolean).forEach(function(pair){
    var parts = pair.split(":");
    if (parts.length === 2) map.set(parts[0], parts[1]);
  });
  return map;
}
var AGENT_KEYS = parseAgentKeys();

// ---- Replay guard (in-memory) ----
var usedJTI = new Map();
setInterval(function(){
  var now = Date.now();
  for (var it of usedJTI.entries()) {
    var jti = it[0], exp = it[1];
    if (exp <= now) usedJTI.delete(jti);
  }
}, 30000);

// ---- App ----
var app = express();
app.use(cors(corsOptions));
app.use(express.json());

// ---- Auth ----
function strictAuth(req, res, next) {
  var auth = req.headers.authorization || "";
  var token = auth.indexOf("Bearer ") === 0 ? auth.slice(7) : null;
  if (!token) return res.status(401).json({ error: "missing_token" });
  try {
    var payload = jwt.verify(token, JWT_SECRET, { issuer: JWT_ISSUER });
    if (!payload.jti) return res.status(401).json({ error: "missing_jti" });
    if (usedJTI.has(payload.jti)) return res.status(401).json({ error: "replay_detected" });
    usedJTI.set(payload.jti, Date.now() + TOKEN_TTL_SECONDS * 1000);
    req.user = payload;
    next();
  } catch (e) {
    return res.status(401).json({ error: "invalid_token", message: e.message });
  }
}
function auth(req, res, next) { return MODE === "dev" ? next() : strictAuth(req, res, next); }

// ---- Dump append (newline-safe) ----
function appendEvent(obj) {
  try {
    var needsNL = fs.existsSync(dumpPath) && fs.statSync(dumpPath).size > 0;
    var prefix = needsNL ? "\n" : "";
    fs.appendFileSync(dumpPath, prefix + JSON.stringify(obj));
  } catch (e) {}
}

// ---- Routes ----
app.get("/health", function(_req, res) {
  res.json({ status: "ok", service: "apiBridge.clean", time: new Date().toISOString() });
});

app.post("/auth/token", function(req, res) {
  var body = req.body || {};
  var agentId = body.agentId;
  var apiKey = body.apiKey;
  var role = body.role || "agent";
  if (!agentId || !apiKey) return res.status(400).json({ error: "agentId_and_apiKey_required" });
  var expected = AGENT_KEYS.get(agentId);
  if (!expected || expected !== apiKey) return res.status(401).json({ error: "invalid_agent_key" });
  var jti = require("crypto").randomBytes(12).toString("hex");
  var token = jwt.sign({ sub: agentId, role: role }, JWT_SECRET, { issuer: JWT_ISSUER, expiresIn: String(TOKEN_TTL_SECONDS) + "s", jwtid: jti });
  res.json({ token: token, expiresIn: TOKEN_TTL_SECONDS, jti: jti, mode: MODE });
});

app.post("/nugget/create", auth, function(req, res) {
  var payload = {
    id: (req.body && req.body.nuggetId) ? req.body.nuggetId : ("nugget_" + Date.now()),
    sessionId: (req.body && req.body.sessionId) ? req.body.sessionId : "dev-session",
    data: (req.body && (req.body.data !== undefined && req.body.data !== null)) ? req.body.data : (req.body || {}),
    createdAt: Date.now()
  };
  appendEvent({ ts: Date.now(), event: "nugget.create", payload: payload });
  res.json({ status: "queued", payload: payload });
});

// ---- Start ----
console.log("[env] MODE=" + MODE + " HTTP=" + PORT_HTTP + " WS=" + PORT_WS + " ORIGINS=" + (ALLOWED.join(",") || "(any)"));
var server = app.listen(PORT_HTTP, function(){ console.log("[apiBridge.clean] HTTP on :" + PORT_HTTP); });

// WS
var wss = new WebSocket.Server({ port: PORT_WS });
wss.on("connection", function(ws){
  ws.send(JSON.stringify({ type: "hello", ts: Date.now() }));
});
console.log("[apiBridge.clean] WS on :" + PORT_WS);
