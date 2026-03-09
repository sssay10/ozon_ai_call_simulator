import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Skip ESLint (including prettier) during production builds so Docker image can be built
  // without failing on formatting-only issues. You can still run `next lint` locally.
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
