import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // HTML must reference the current deployment's hashed CSS and JS files.
  // Keep immutable caching on the assets themselves for fast repeat visits.
  async headers() {
    return ['/', '/demo'].map((source) => ({
      source,
      headers: [{ key: 'Cache-Control', value: 'no-store, must-revalidate' }],
    }));
  },
};

export default nextConfig;
