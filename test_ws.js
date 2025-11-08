import WebSocket from "ws";

const ws = new WebSocket("ws://127.0.0.1:8000/ws");

ws.on("open", () => {
  console.log("✅ Connected to FastAPI WebSocket");
  ws.send("Hello from Node 22!");
});

ws.on("message", (msg) => {
  console.log("📩 Received:", msg.toString());
});

ws.on("close", () => console.log("❌ Connection closed"));
ws.on("error", (err) => console.error("⚠️ WebSocket error:", err));
