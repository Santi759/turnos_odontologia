FROM node:22.23.1-trixie-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

EXPOSE 5173
