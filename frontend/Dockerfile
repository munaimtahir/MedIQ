# Multi-stage production Dockerfile for Next.js frontend
# Stage 1: Build
FROM node:20-alpine AS builder

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /build

# Copy package files first (for better layer caching)
COPY package.json pnpm-lock.yaml ./

# Install dependencies with frozen lockfile
RUN pnpm install --frozen-lockfile --prod=false

# Copy source files
COPY . .

# Build Next.js application with standalone output
# Standalone mode creates a minimal server with only required dependencies
RUN pnpm run build

# Stage 2: Runtime (standalone Node.js server)
FROM node:20-alpine

# Install wget for health check
RUN apk add --no-cache wget

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

WORKDIR /app

# Copy standalone build output from builder
# Next.js standalone creates .next/standalone directory with minimal runtime
# The standalone directory contains server.js, node_modules, and package.json
# We copy the contents of standalone to /app root
COPY --from=builder --chown=nextjs:nodejs /build/.next/standalone ./

# Copy static files (standalone mode requires these alongside the standalone output)
# Static files go into .next/static relative to where server.js runs
COPY --from=builder --chown=nextjs:nodejs /build/.next/static ./.next/static

# Copy public files (required for static assets)
COPY --from=builder --chown=nextjs:nodejs /build/public ./public

# Set Node.js production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Switch to non-root user
USER nextjs

# Expose internal port (not exposed to host - accessed via Traefik)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# OCI labels for metadata
LABEL org.opencontainers.image.source="https://github.com/your-org/exam-prep-platform" \
      org.opencontainers.image.revision="${GITHUB_SHA:-unknown}" \
      org.opencontainers.image.created="${BUILD_DATE:-unknown}" \
      org.opencontainers.image.title="Exam Prep Platform Frontend" \
      org.opencontainers.image.description="Next.js frontend for medical exam practice platform"

# Start Next.js standalone server
CMD ["node", "server.js"]
