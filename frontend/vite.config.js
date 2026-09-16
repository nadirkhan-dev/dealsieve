import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The static preview is served from https://nadirkhan-dev.github.io/dealsieve/,
// so it needs a sub-path base. Every other build stays at the root.
export default defineConfig(() => {
  const isStatic = process.env.VITE_STATIC === "true";
  return {
    plugins: [react()],
    base: isStatic ? "/dealsieve/" : "/",
    server: {
      proxy: { "/api": "http://localhost:8000" },
    },
  };
});
