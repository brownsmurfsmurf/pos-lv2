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
    "src/components/**/*.tsx",
    // 画面のオーケストレーションと通信層は結合・機能テスト（IT/ST）で検証する
    "!src/lib/bff.ts",
    "!src/lib/apiClient.ts",
    "!src/components/PosScreen.tsx",
    "!src/components/LoginForm.tsx",
    "!src/features/cart/useCartStore.ts",
  ],
  coverageThreshold: {
    global: { statements: 80, branches: 70, functions: 90, lines: 80 },
  },
};

export default createJestConfig(config);
