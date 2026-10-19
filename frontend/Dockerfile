# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Vite inlines env vars at build time, so the API URL is a build argument, not a runtime env.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.30-alpine AS runtime
# Pull Alpine security fixes that landed after the base image was built (e.g. libexpat
# CVE-2026-77214), so the image does not wait on an upstream rebuild to pass the Trivy gate.
# The base image runs as UID 101; switch to root only for the upgrade, then drop back.
USER root
RUN apk upgrade --no-cache
USER 101
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
