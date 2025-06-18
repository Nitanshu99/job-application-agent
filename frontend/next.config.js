/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // <-- Add this line!
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;