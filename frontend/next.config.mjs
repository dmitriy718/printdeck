/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  distDir: "dist",
  trailingSlash: false,
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 960, 1280, 1600, 1920, 2560],
    unoptimized: false,
  },
  experimental: {
    optimizeCss: true,
  },
};

export default nextConfig;
