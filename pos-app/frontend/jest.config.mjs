import nextJest from "next/jest.js";

const createJestConfig = nextJest({ dir: "./" });

/** @type {import('jest').Config} */
const config = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/src/$1" },
  testMatch: ["<rootDir>/__tests__/**/*.test.(ts|tsx)"],
  collectCoverageFrom: [
    "src/lib/**/*.ts",
    "src/features/cart/**/*.ts",
    "src/features/scanner/debounce.ts",
    "src/components/**/*.tsx",
    // 通信の層は結合テスト（IT）で確かめる
    "!src/lib/bff.ts",
    "!src/lib/apiClient.ts",
  ],
  coverageThreshold: {
    global: { statements: 80, branches: 70, functions: 90, lines: 80 },
  },
};

export default createJestConfig(config);
