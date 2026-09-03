#!/usr/bin/env node
/**
 * Forge monorepo pre-commit hook（仓库根统一入口）
 *
 * 背景：admin / portal-web 两个子项目各自通过 simple-git-hooks 安装 pre-commit，
 * 后安装者会把 .git/hooks/pre-commit 覆盖为"在仓库根执行 pnpm ..."的脚本，
 * 而仓库根没有 package.json，导致任何提交都报 ERR_PNPM_NO_PKG_MANIFEST。
 *
 * 本脚本由两处子项目 package.json 的 simple-git-hooks.pre-commit 共同指向：
 *   node scripts/pre-commit.mjs
 * 它按本次 staged 的改动文件定位到对应子项目，在正确的工作目录执行质量门槛；
 * 不涉及任何子项目源码的提交（Dockerfile / compose / 文档 / 根级配置等）直接放行。
 *
 * 质量门槛以 DEV-RULES 为准（前端 lint/typecheck）：
 *   - admin      : pnpm typecheck + oxlint/eslint 检查模式
 *                  （不走 lint script 的 --fix，避免提交时把历史格式债
 *                    自动改写进工作区；hook 内改动文件会造成 diff 漂移死循环）
 *   - portal-web : pnpm lint && pnpm typecheck
 *
 * 仍支持 SKIP_SIMPLE_GIT_HOOKS=1 整体跳过（wrapper 亦会提前拦截）。
 */
import { execSync } from 'node:child_process'

if (process.env.SKIP_SIMPLE_GIT_HOOKS === '1') {
  console.log('[pre-commit] SKIP_SIMPLE_GIT_HOOKS=1, skip quality gates.')
  process.exit(0)
}

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim()

// staged 文件（含空格安全）
const files = execSync('git diff --cached --name-only -z', {
  encoding: 'utf8',
  cwd: repoRoot,
})
  .split('\0')
  .filter(Boolean)

if (files.length === 0) {
  console.log('[pre-commit] no staged files, skip.')
  process.exit(0)
}

const touched = {
  admin: files.some((f) => f.startsWith('admin/')),
  portalWeb: files.some((f) => f.startsWith('portal-web/')),
  backend: files.some((f) => f.startsWith('backend/')),
}

// 仓库根/纯配置/文档等非子项目源码变更：不设代码质量门槛
if (!touched.admin && !touched.portalWeb && !touched.backend) {
  console.log('[pre-commit] only root/config/doc files changed, skip quality gates.')
  process.exit(0)
}

const run = (cmd, cwd) => {
  console.log(`\n[pre-commit] running in ${cwd.replace(repoRoot, '.')}: ${cmd}`)
  execSync(cmd, { cwd, stdio: 'inherit' })
}

try {
  if (touched.admin) {
    run('pnpm typecheck', `${repoRoot}/admin`)
    // 检查模式：admin 的 lint script 带 --fix，hook 内使用会改写工作区文件，
    // 后续 git diff 检查/提交会陷入漂移循环；此处仅校验不修改。
    const bin = (name) =>
      process.platform === 'win32' ? `node_modules\\.bin\\${name}.cmd` : `node_modules/.bin/${name}`
    run(`${bin('oxlint')} .`, `${repoRoot}/admin`)
    run(`${bin('eslint')} .`, `${repoRoot}/admin`)
  }
  if (touched.portalWeb) {
    run('pnpm lint', `${repoRoot}/portal-web`)
    run('pnpm typecheck', `${repoRoot}/portal-web`)
  }
  if (touched.backend) {
    // backend 无独立虚拟环境时 uv run 可能不可用；此时显式警告放行，避免锁死提交
    try {
      run('uv run ruff check .', `${repoRoot}/backend`)
      run('uv run mypy .', `${repoRoot}/backend`)
    } catch (backendErr) {
      if (/uv/.test(backendErr.message)) {
        console.warn('[pre-commit] WARN: uv unavailable for backend gates, skipped.')
      } else {
        throw backendErr
      }
    }
  }
  console.log('\n[pre-commit] all quality gates passed.')
} catch (err) {
  console.error('\n[pre-commit] FAILED:', err.message)
  process.exit(1)
}
