# Frontend Dockerfile - Multi-stage build
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY package-lock.json ./
RUN npm ci --only=production && npm cache clean --force

# Development stage
FROM base AS dev
WORKDIR /app
COPY package*.json ./
COPY package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Build stage
FROM base AS builder
WORKDIR /app
COPY package*.json ./
COPY package-lock.json ./
RUN npm ci

COPY . .

# Create next.config.js if it doesn't exist
RUN if [ ! -f next.config.js ]; then \
    echo "/** @type {import('next').NextConfig} */" > next.config.js && \
    echo "const nextConfig = {" >> next.config.js && \
    echo "  reactStrictMode: true," >> next.config.js && \
    echo "  swcMinify: true," >> next.config.js && \
    echo "  env: {" >> next.config.js && \
    echo "    API_URL: process.env.API_URL || 'http://localhost:8000'," >> next.config.js && \
    echo "  }," >> next.config.js && \
    echo "};" >> next.config.js && \
    echo "module.exports = nextConfig;" >> next.config.js; \
    fi

# Build the application
RUN npm run build

# Production stage
FROM base AS production
WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
