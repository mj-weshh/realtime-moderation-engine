import { consumer } from "./kafkaClient.js";

async function main() {
  await consumer.connect();
  await consumer.subscribe({ topic: "scored_comments", fromBeginning: false });

  console.log("Connected to Kafka; listening on scored_comments ...");

  await consumer.run({
    eachMessage: async ({ message }) => {
      const payload = JSON.parse(message.value.toString());
      console.log(payload);
    },
  });
}

main().catch((err) => {
  console.error("Kafka consumer failed:", err);
  process.exit(1);
});
