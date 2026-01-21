import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export', // Force la génération d'un site statique (HTML/CSS/JS)
  images: {
    unoptimized: true, // Requis pour l'export statique (pas de serveur d'images Node.js)
  },
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
  
};

export default nextConfig;
