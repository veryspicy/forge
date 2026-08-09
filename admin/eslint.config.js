import { defineConfig } from '@sa/eslint-config';

export default defineConfig({
  'vue/component-name-in-template-casing': [
    'warn',
    'PascalCase',
    {
      registeredComponentsOnly: false,
      ignores: ['/^icon-/']
    }
  ]
});
