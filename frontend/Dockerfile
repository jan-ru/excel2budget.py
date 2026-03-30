# Frontend Dockerfile — Vite build → nginx
# Multi-stage: Node build, then serve static files with nginx

# --- Build stage ---
FROM node:18-slim AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Point API URL to relative path so nginx proxy handles it
ENV VITE_API_URL=""
RUN npm run build

# --- Production stage ---
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
