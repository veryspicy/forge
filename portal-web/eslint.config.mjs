import { createConfigForNuxt } from '@nuxt/eslint-config/flat'

export default [
  ...(await createConfigForNuxt({
    features: {
      tooling: true,
      stylistic: false,
    },
  })),
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      'unicorn/prefer-number-properties': 'off',
      'regexp/no-unused-capturing-group': 'off',
      'regexp/no-super-linear-backtracking': 'off',
      '@typescript-eslint/no-unused-vars': 'warn',
      'vue/no-unused-vars': 'warn',
      'import/first': 'warn',
      'no-useless-catch': 'off',
      'vue/no-multiple-template-root': 'off',
    },
  },
]
