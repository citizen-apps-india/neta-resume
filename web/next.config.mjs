/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    // Server-side base URL for the FastAPI read layer.
    NETA_API_BASE: process.env.NETA_API_BASE ?? "http://localhost:8000",
  },
};

export default nextConfig;
