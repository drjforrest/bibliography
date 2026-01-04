/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
  // Set the output file tracing root to the project root
  // This resolves the warning about multiple lockfiles
  outputFileTracingRoot: path.join(__dirname, '../../'),
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.counterforce-hero.tech https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://js.sentry-cdn.com https://browser.sentry-cdn.com https://*.sentry.io https://challenges.cloudflare.com https://static.cloudflareinsights.com https://scdn.clerk.com https://segapi.clerk.com https://*.protect.clerk.com https://*.client.protect.clerk.com https://clerk-telemetry.com https://clerk.com https://api.stripe.com https://maps.googleapis.com https://*.js.stripe.com https://js.stripe.com",
              "worker-src 'self' blob: https://*.clerk.com https://cdnjs.cloudflare.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data: https: blob:",
              "connect-src 'self' https://*.counterforce-hero.tech https://*.sentry.io https://*.clerk.com https://clerk-telemetry.com https://static.cloudflareinsights.com https://api.stripe.com",
              "frame-src 'self' https://*.clerk.com https://js.stripe.com",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join('; '),
          },
        ],
      },
    ];
  },
  async rewrites() {
    // For server-side rewrites, always use localhost backend
    // Client-side calls will use NEXT_PUBLIC_API_URL directly
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8400';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
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
