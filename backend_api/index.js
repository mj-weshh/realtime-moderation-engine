import express from "express";
import http from "http";
import { WebSocketServer, WebSocket } from "ws";
import { consumer } from "./kafkaClient.js";

const PORT = Number(process.env.PORT ?? "8081");
const TOXICITY_THRESHOLD = Number(process.env.TOXICITY_THRESHOLD ?? "0.5");

function shouldBroadcast(payload) {
  if (!payload.is_flagged) return false;
  const toxicity = payload.scores?.toxicity ?? 0;
  return toxicity >= TOXICITY_THRESHOLD;
}

function broadcastToClients(wss, payload) {
  const data = JSON.stringify(payload);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(data);
    }
  }
}

async function main() {
  const app = express();
  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  const server = http.createServer(app);
  const wss = new WebSocketServer({ server });

  wss.on("connection", (ws) => {
    console.log("WebSocket client connected");
    ws.on("close", () => {
      console.log("WebSocket client disconnected");
    });
  });

  await new Promise((resolve) => {
    server.listen(PORT, () => {
      console.log(`HTTP and WebSocket server listening on port ${PORT}`);
      resolve();
    });
  });

  await consumer.connect();
  await consumer.subscribe({ topic: "scored_comments", fromBeginning: false });

  console.log("Connected to Kafka; listening on scored_comments ...");

  await consumer.run({
    eachMessage: async ({ message }) => {
      const payload = JSON.parse(message.value.toString());
      if (!shouldBroadcast(payload)) return;

      broadcastToClients(wss, payload);
    },
  });
}

main().catch((err) => {
  console.error("Backend API failed:", err);
  process.exit(1);
});
