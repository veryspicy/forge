---
name: Pull Request
title: '<type>(<scope>): <subject>'
labels: []
assignees: []
---

## 变更摘要

<!-- 一句话说明本次变更内容，遵循 Conventional Commits：feat/fix/docs/refactor/perf/test/chore/ci -->

- 类型：
- 范围（可选）：
- 描述：

## 变更清单

- [ ] 变更范围与 §1.4 描述一致（对应 CI paths-filter）
- [ ] 不涉及非本次目标的无关改动

## 质量门槛（提交前自查）

- [ ] Backend：`ruff` / `mypy` 通过（如涉及 backend/）
- [ ] Frontend：`lint` / `typecheck` 通过（如涉及前端）
- [ ] 无调试残留（print / console.log / 临时注释）
- [ ] 无敏感信息（密码 / API Key / .env）
- [ ] 无备份文件（*_backup.py / *_old.py / *_202*.py）

## 本地验证结果

<!-- 单人流程：本地部署验证结论 + 用户确认状态 -->

- [ ] 已本地部署验证，用户确认通过（如涉及代码行为变更）

## 关联项

- 关联 Issue / 需求：
- 关联提交：
- 涉及迁移（migration）：
  - [ ] 已在容器内执行 `podman exec forge-backend alembic upgrade head` 并先备份
  - [ ] 不涉及

## CI 状态

<!-- 由合并人（单人即开发者本人）在 CI 完成后勾选 -->

- [ ] PR CI 健康（对应 run 为 success；docs-only 时测试 job 按 §1.4 允许跳过）
- [ ] push dev 后最终 CI run 健康

## 测试说明

<!-- 说明本次变更如何验证：单测覆盖、手动测试步骤、涉及服务 -->
