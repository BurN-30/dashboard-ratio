import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  webpack(config) {
    config.module.rules.push({
      test: /\.svg$/,
      use: ["@svgr/webpack"],
    });
    return config;
  },
    
    turbopack: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  async rewrites() {
    return [
      {
        source: '/api/hardware/:path*',
        destination: 'http://localhost:5056/api/:path*',
      },
    ];
  },
};

export default nextConfig;
