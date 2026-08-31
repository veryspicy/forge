import { Config } from 'eslint/config';

declare function defineConfig(overrides?: Record<string, string>): Promise<Config[]>;
export { defineConfig };
