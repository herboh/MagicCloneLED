/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    // Only apply a rewrite if targeting an absolute API URL
    const api = process.env.NEXT_PUBLIC_API_URL;
    if (api && api.startsWith("http")) {
      return [
        {
          source: "/api/:path*",
          destination: `${api}/:path*`,
        },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
