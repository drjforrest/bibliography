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
    // CSP directives organized for maintainability and security auditing
    const cspDirectives = {
      'default-src': ["'self'"],
      'script-src': [
        "'self'",
        "'unsafe-inline'", // Required for Next.js
        "'unsafe-eval'", // Required for Next.js dev mode and some libraries
        // Application domains
        'https://*.counterforce-hero.tech',
        // CDN - jsDelivr (for specific libraries if needed)
        'https://cdn.jsdelivr.net',
        // Sentry error tracking
        'https://js.sentry-cdn.com',
        'https://browser.sentry-cdn.com',
        'https://*.sentry.io',
        // Cloudflare
        'https://challenges.cloudflare.com',
        'https://static.cloudflareinsights.com',
        // Clerk authentication
        'https://scdn.clerk.com',
        'https://segapi.clerk.com',
        'https://*.protect.clerk.com',
        'https://*.client.protect.clerk.com',
        'https://clerk-telemetry.com',
        'https://clerk.com',
        // Stripe payments
        'https://api.stripe.com',
        'https://*.js.stripe.com',
        'https://js.stripe.com',
        // Google Maps
        'https://maps.googleapis.com',
      ],
      'worker-src': [
        "'self'",
        'blob:', // Required for PDF.js and other blob workers
        // Clerk workers
        'https://*.clerk.com',
        // Note: cdnjs.cloudflare.com removed - PDF.js worker now self-hosted
      ],
      'style-src': [
        "'self'",
        "'unsafe-inline'", // Required for styled-components, Tailwind, etc.
        // Google Fonts
        'https://fonts.googleapis.com',
        // CDN - jsDelivr (for specific CSS libraries if needed)
        'https://cdn.jsdelivr.net',
      ],
      'font-src': [
        "'self'",
        // Google Fonts
        'https://fonts.gstatic.com',
        // Scite.ai fonts
        'https://cdn.scite.ai',
      ],
      'img-src': [
        "'self'",
        'data:', // For inline images and data URIs
        'https:', // Allow all HTTPS images (may need to restrict further)
        'blob:', // For blob URLs
      ],
      'connect-src': [
        "'self'",
        // Application API
        'https://*.counterforce-hero.tech',
        // Sentry
        'https://*.sentry.io',
        // Clerk
        'https://*.clerk.com',
        'https://clerk-telemetry.com',
        // Cloudflare
        'https://static.cloudflareinsights.com',
        // Stripe
        'https://api.stripe.com',
      ],
      'frame-src': [
        "'self'",
        // Clerk iframes
        'https://*.clerk.com',
        // Stripe iframes
        'https://js.stripe.com',
      ],
      'object-src': ["'none'"], // Block all object, embed, and applet elements
      'base-uri': ["'self'"], // Restrict base tag URLs
      'form-action': ["'self'"], // Restrict form submissions
    };

    // Build CSP string from directives object
    const cspString = Object.entries(cspDirectives)
      .map(([directive, sources]) => `${directive} ${sources.join(' ')}`)
      .join('; ');

    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: cspString,
          },
        ],
      },
    ];
  },
  async rewrites() {
    // For server-side rewrites, always use localhost backend
    // Client-side calls will use NEXT_PUBLIC_API_URL directly
    // Default to 8000 for development, 8400 for production
    const backendUrl = process.env.BACKEND_URL || 
      (process.env.NODE_ENV === 'production' ? 'http://localhost:8400' : 'http://localhost:8000');
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
