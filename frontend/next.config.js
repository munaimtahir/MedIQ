/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Transpile packages for proper module resolution
  transpilePackages: ["@radix-ui/react-toast"],
  
  // React 19 compiler for automatic optimizations
  reactCompiler: true,
  
  // Experimental features for performance
  experimental: {
    // Optimize CSS handling
    optimizeCss: true,
  },
  
  // Image optimization
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    minimumCacheTTL: 60,
    dangerouslyAllowSVG: true,
    contentDispositionType: "attachment",
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  
  // Optimize on-demand entries
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },
  
  // Enable standalone output for Docker (minimal runtime dependencies)
  output: 'standalone',
};

module.exports = nextConfig;
