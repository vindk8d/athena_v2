/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },
  images: {
    unoptimized: true,
  },
  // Add rewrite rule to redirect root to the Next.js app
  async rewrites() {
    return [
      {
        source: '/',
        destination: '/index',
      },
    ];
  },
};

module.exports = nextConfig;
