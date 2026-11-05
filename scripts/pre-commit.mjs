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
import { execSync, spawnSync } from 'node:child_process'
import { existsSync, readdirSync } from 'node:fs'
import { homedir } from 'node:os'
import path from 'node:path'

if (process.env.SKIP_SIMPLE_GIT_HOOKS === '1') {
  console.log('[pre-commit] SKIP_SIMPLE_GIT_HOOKS=1, skip quality gates.')
  process.exit(0)
}

// ── node 版本守卫 ────────────────────────────────────────────────
// 背景：hook 由 simple-git-hooks 以宿主默认 node 启动（本机曾为 v22.12.0），
// 而 pnpm 11.x 要求 node >= 22.13，导致 `pnpm lint` 直接报错、提交被拦。
// 处理：若当前 node 低于门槛，自动在 fnm / nvm / volta 安装目录中挑选满足
//       条件的最高版本 node 重新执行本脚本，并把其所在目录前置到 PATH，
//       使后续 pnpm / vue-tsc 子进程也使用该 node。
const MIN_NODE = [22, 13]
const REENTRY_FLAG = 'FORGE_HOOK_NODE_REEXEC'

const parseVer = (v) => v.replace(/^v/, '').split('.').map((n) => Number.parseInt(n, 10) || 0)
const verGte = (a, b) => {
  for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
    const x = a[i] ?? 0
    const y = b[i] ?? 0
    if (x !== y) return x > y
  }
  return true
}

const nodeRoots = () => {
  const roots = []
  const push = (p) => p && roots.push(p)
  if (process.platform === 'win32') {
    push(process.env.FNM_DIR)
    push(process.env.APPDATA && path.join(process.env.APPDATA, 'fnm', 'node-versions'))
    push(process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'fnm', 'node-versions'))
    push(process.env.NVM_HOME)
    push(process.env.APPDATA && path.join(process.env.APPDATA, 'nvm'))
    push(path.join(homedir(), '.volta', 'tools', 'image', 'node'))
  } else {
    push(path.join(homedir(), 'Library', 'Application Support', 'fnm', 'node-versions'))
    push(path.join(homedir(), '.local', 'share', 'fnm', 'node-versions'))
    push(path.join(homedir(), '.nvm', 'versions', 'node'))
    push(path.join(homedir(), '.volta', 'tools', 'image', 'node'))
  }
  return roots.filter((d) => existsSync(d))
}

const nodeExeIn = (versionDir) => {
  const exe = process.platform === 'win32' ? 'node.exe' : 'node'
  return [
    path.join(versionDir, exe), // fnm(windows) / nvm(windows) / volta
    path.join(versionDir, 'installation', 'bin', exe), // fnm(unix)
    path.join(versionDir, 'bin', exe), // nvm(unix)
  ].find((p) => existsSync(p))
}

const findCompliantNode = () => {
  let best = null
  for (const root of nodeRoots()) {
    let entries = []
    try {
      entries = readdirSync(root)
    } catch {
      continue
    }
    for (const name of entries) {
      if (!/^v?\d+\.\d+\.\d+$/.test(name)) continue
      const ver = parseVer(name)
      if (!verGte(ver, MIN_NODE)) continue
      const exe = nodeExeIn(path.join(root, name))
      if (!exe) continue
      if (!best || verGte(ver, best.ver)) best = { ver, exe, dir: path.dirname(exe) }
    }
  }
  return best
}

const ensureNodeVersion = () => {
  if (process.env[REENTRY_FLAG] === '1') return
  if (verGte(parseVer(process.versions.node), MIN_NODE)) return

  const alt = findCompliantNode()
  if (!alt) {
    console.error(
      `\n[pre-commit] FAILED: 当前 node v${process.versions.node} 低于前端门槛 v${MIN_NODE.join('.')}（pnpm 11.x 要求）`,
    )
    console.error('[pre-commit] 未在 fnm / nvm / volta 目录找到合规 node，请先安装 node >= ' + MIN_NODE.join('.'))
    process.exit(1)
  }

  console.log(
    `[pre-commit] node v${process.versions.node} 低于前端门槛 v${MIN_NODE.join('.')}，切换至 ${alt.exe}`,
  )
  const basePath = process.env.PATH ?? ''
  const child = spawnSync(alt.exe, [process.argv[1], ...process.argv.slice(2)], {
    stdio: 'inherit',
    cwd: process.cwd(),
    env: {
      ...process.env,
      [REENTRY_FLAG]: '1',
      PATH: `${alt.dir}${path.delimiter}${basePath}`,
    },
  })
  process.exit(child.status ?? 1)
}

ensureNodeVersion()

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
