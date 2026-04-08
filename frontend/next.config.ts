import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone pour Docker, undefined sur Vercel pour le mode demo
  output: process.env.VERCEL ? undefined : 'standalone',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
