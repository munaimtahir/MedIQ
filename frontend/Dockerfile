FROM node:20-alpine

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy package files first (layer caching optimization)
COPY package.json pnpm-lock.yaml ./

# Install dependencies with frozen lockfile for consistency
RUN pnpm install --frozen-lockfile

# Copy source files
COPY . .

# Create .next directory for cache volume mount
RUN mkdir -p .next

EXPOSE 3000

CMD ["pnpm", "run", "dev"]

