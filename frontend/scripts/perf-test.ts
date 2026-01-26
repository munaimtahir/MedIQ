/**
 * Simple performance test script
 * Measures key performance metrics for the landing page
 * 
 * Run with: pnpm ts-node scripts/perf-test.ts
 * 
 * For full testing, consider using Playwright or Lighthouse CI
 */

interface PerformanceMetrics {
  FCP?: number; // First Contentful Paint
  LCP?: number; // Largest Contentful Paint
  CLS?: number; // Cumulative Layout Shift
  TTFB?: number; // Time to First Byte
}

async function testPerformance(url: string = "http://localhost:3000"): Promise<void> {
  console.log(`\n=== Performance Test ===`);
  console.log(`Testing: ${url}\n`);

  try {
    // Basic check if server is running
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    console.log("✓ Server is running");
    console.log(`✓ Status: ${response.status}`);
    console.log(`✓ Content-Type: ${response.headers.get("content-type")}`);

    // Check bundle size from headers
    const contentLength = response.headers.get("content-length");
    if (contentLength) {
      const sizeKB = parseInt(contentLength) / 1024;
      console.log(`✓ HTML Size: ${sizeKB.toFixed(2)} KB`);
    }

    console.log("\n📊 To measure Web Vitals:");
    console.log("  1. Open http://localhost:3000 in Chrome");
    console.log("  2. Open DevTools > Performance");
    console.log("  3. Record and check metrics");
    console.log("\n📦 To analyze bundle size:");
    console.log("  pnpm analyze");
    console.log("\n🔍 To run Lighthouse:");
    console.log("  npx lighthouse http://localhost:3000 --view");
  } catch (error) {
    console.error("✗ Performance test failed:", error);
    console.log("\nMake sure your dev server is running:");
    console.log("  pnpm dev");
  }
}

// Run if called directly
if (require.main === module) {
  testPerformance().catch(console.error);
}

export { testPerformance };
