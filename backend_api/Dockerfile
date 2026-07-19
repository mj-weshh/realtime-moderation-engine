FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --omit=dev

COPY index.js kafkaClient.js ./

EXPOSE 8081

CMD ["node", "index.js"]
