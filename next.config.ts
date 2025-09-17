import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Tell Turbopack where the app root is when Next infers the workspace root as repo root
  turbopack: {
    root: './frontend',
  } as any,
};

export default nextConfig;
