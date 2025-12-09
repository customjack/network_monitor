/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  trailingSlash: true,
  basePath: '/network_monitor',
  assetPrefix: '/network_monitor/',
};

module.exports = nextConfig;
