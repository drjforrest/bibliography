/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
  webpack: (config, { isServer }) => {
    // Fix for react-pdf/pdfjs-dist with Next.js 15
    config.resolve.alias.canvas = false;
    config.resolve.alias.encoding = false;
    
    // Exclude pdfjs-dist from server-side bundling
    if (isServer) {
      config.externals = [...(config.externals || []), 'canvas', 'pdfjs-dist'];
    }
    
    // Handle pdfjs-dist worker properly
    config.module = config.module || {};
    config.module.rules = config.module.rules || [];
    
    config.module.rules.push({
      test: /pdf\.worker\.(min\.)?js/,
      type: 'asset/resource',
      generator: {
        filename: 'static/worker/[hash][ext][query]',
      },
    });
    
    return config;
  },
};

module.exports = nextConfig;
