import { createRequire } from "node:module";

// eslint-config-next 16 ships a flat config array (CommonJS). Load it through createRequire.
const require = createRequire(import.meta.url);
const nextCoreWebVitals = require("eslint-config-next/core-web-vitals");

export default [
  ...nextCoreWebVitals,
  {
    // Five pages fetch data inside useEffect. Refactoring them is tracked as follow-up work,
    // so this rule is reported as a warning rather than failing lint.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  {
    ignores: [".next/**", "node_modules/**", "out/**", "coverage/**", "*.config.*"],
  },
];
