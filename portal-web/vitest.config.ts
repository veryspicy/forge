import { defineVitestConfig } from "@nuxt/test-utils/config";

export default defineVitestConfig({
  test: {
    environment: "nuxt",
    environmentOptions: {
      nuxt: {
        domEnvironment: "happy-dom",
      },
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["app/components/**/*.vue", "app/composables/**/*.ts", "app/stores/**/*.ts", "app/pages/**/*.vue"],
    },
    globals: true,
    include: ["tests/**/*.test.ts"],
  },
});
