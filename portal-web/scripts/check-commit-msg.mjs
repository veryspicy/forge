// portal-web commit-msg 校验：强制 Conventional Commits 格式（规则见 DEV-RULES §15）
// 由 simple-git-hooks 在 commit-msg 阶段调用，cwd 为仓库根。
import { readFileSync } from "node:fs";

const messageFile = process.argv[2] || ".git/COMMIT_EDITMSG";
const content = readFileSync(messageFile, "utf8");

// 跳过 merge / revert 等 git 自动生成的消息
const firstLine = content.split("\n")[0].trim();
if (/^(merge|revert|fixup!|squash!)/i.test(firstLine)) {
  process.exit(0);
}

const CONVENTIONAL_RE = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([\w-]+\))?!?: .+$/;

if (!CONVENTIONAL_RE.test(firstLine)) {
  console.error(
    [
      "commit message 不符合 Conventional Commits 规范：",
      "",
      `  收到: ${firstLine}`,
      "",
      "  格式: <type>(<scope>): <subject>",
      "  示例: feat(portal-web): 增加订单列表筛选",
      "        fix: 修复登录态失效问题",
      "        chore: 更新依赖版本",
      "  允许 type: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert",
    ].join("\n"),
  );
  process.exit(1);
}

process.exit(0);
