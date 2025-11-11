[S2｜完成度 100%]
# AGENTS

## Project Snapshot
- 完成度：100%（基于TASKS.md与测试通过）
- 结构：符合 `project-structure` 规范（根目录精简、docs/PLAN|REQUIRES|TASKS、data→外部存储、uv 管理）并提供 CLI `dplk`
- 规模：核心模块（config/paths/client/sharing/cli/diagnostics/structure）+ 测试用例
- 质量信号：19 tests passed（uv run pytest）；结构/环境 doctor 全通过；无TODO/FIXME/HACK
- 文档一致性：README/PLAN/TASKS 与实现一致，额外指南移入 docs/guides

## Rolling TODO
- [x] Task-1: 创建项目基础结构（完成）
- [x] Task-2: 实现Dropbox API集成模块（完成）
- [x] Task-3: 实现路径校验逻辑（完成）
- [x] Task-4~10: CLI、共享链接幂等、剪贴板、错误处理与日志、配置、测试与README（完成）

## Replan
- 进入维护阶段：准备实际使用与后续小迭代（如更多输出格式/批量处理——若需要）

## Run Log
- 2025-11-11 迁移至 uv_build，新增结构/环境 doctor + diagnostics 子命令，重构调试脚本为模块，更新 README/AGENTS，uv lock + tests 通过
- 2025-10-21 实现核心模块与CLI，集成Dropbox SDK，完成路径校验与错误处理
- 2025-10-21 补充剪贴板与日志功能，完善README
- 2025-10-21 编写并通过测试（13 passed），更新TASKS与AGENTS快照
