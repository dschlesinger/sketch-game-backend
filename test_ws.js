import WebSocket from "ws";
const http = require('http');

const ws = new WebSocket("ws://127.0.0.1:8000/ws");

ws.on("open", () => {
  console.log("✅ Connected to FastAPI WebSocket");
  ws.send("{\"route\": \"ping_n8n\", \"message\": {}}");
});

ws.on("message", (msg) => {
  console.log("📩 Received:", msg.toString());
});

ws.on("close", () => console.log("❌ Connection closed"));
ws.on("error", (err) => console.error("⚠️ WebSocket error:", err));

