import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        panel: "#f7f7f4",
        line: "#d8d5cc",
        signal: "#0f766e",
        risk: "#b42318",
        amber: "#b45309",
      },
    },
  },
  plugins: [],
};

export default config;
