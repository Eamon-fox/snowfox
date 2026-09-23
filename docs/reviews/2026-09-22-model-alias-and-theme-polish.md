# 2026-09-22 模型别名与统一控件样式

## 范围

涉及 agent_runtime、gui_application、gui_presentation；首轮未修改共享瓶颈点；后续 GLM-5.3 更正串行更新中英文翻译，解释深度思考开关。未改变模块边界或库存执行规则。保留之前清理轮次的未提交改动。

## 官方核对

- [DeepSeek 模型目录](https://api-docs.deepseek.com/quick_start/pricing/)与[更新记录](https://api-docs.deepseek.com/updates/)：`deepseek-flash` 当前对应 V4.1 Flash；旧 `deepseek-v4-flash` / `deepseek-v4-flash-vision-exp` 仅兼容路由。Pro 仍为 `deepseek-v4-pro`。
- 智谱首次核对误用了较旧的介绍页，将 GLM-5.2 当作最新版本。经用户指出后，依据[GLM-5.3 API 文档](https://docs.z.ai/guides/llm/glm-5.3)、[Flash/FlashX 文档](https://docs.z.ai/guides/vlm/glm-5.3-flash)与[定价页](https://docs.z.ai/guides/overview/pricing)更正：默认 `glm-5.3`，并增加 `glm-5.3-flash` / `glm-5.3-flashx` 选项；保留 GLM-4.7。定价页同时列出 `GLM-5.3` / `GLM-5.3-Flash` / `GLM-5.3-FlashX`，与实现一致。5.3 系列强制推理：`thinking.type` 仅接受 `enabled`，`reasoning_effort` 取 `low`/`high`/`max`（默认 `max`），原 `disabled` 写法已不再支持。
- [MiniMax 官方模型调用](https://platform.minimax.io/docs/api-reference/text-anthropic-api)：当前文本 M 系列为 `MiniMax-M3`（1M 上下文），仓库已使用该名称。文档中的 `MiniMax-H3` 是视频生成模型，不属于文本候选，不纳入模型列表。

## 实施

- DeepSeek 默认值与列表改用 `deepseek-flash`，已有配置通过原来的归一化入口迁移。保留 Pro 与自定义模型，不新增模型探测、静默降级或后台更新链路。
- 三个客户端的默认模型、默认 URL 统一引用已有目录，删除重复字面量。
- 公共主题统一 10px 滚动条、36px 最小滑块，提升浅/深色可见度；删除 Pending 的六条专用覆盖和九行样式重刷代码。
- 输入控件与 ghost 按钮的焦点不再增加边框宽度；primary/ghost 补齐按下态，所有 variant 按钮共用禁用态。深色主按钮改用深色文字，提高蓝色背景上的可读性。
- 首轮生产代码新增 24 行、删除 35 行，净减 11 行（不含后续 GLM 更正、文档与测试）；同时移除已无引用的两项边框宽度 token。
- GLM 更正同步升级旧 5.2 配置，并适配 5.3 系列的强制推理要求：关闭深度思考时使用 low，开启时使用 max，避免发送已不支持的 disabled 参数。中英文设置提示同步说明该语义。需要强制推理的模型名收敛为 `ZhipuLLMClient.REASONING_REQUIRED_MODELS` 类常量，请求构造里不再内联重复字面量。

## 验证

- 模型请求、旧配置迁移、设置选项与相关 GUI 专项：161 passed、13 subtests passed。
- 实际 Qt 浅/深色渲染：修改前，行输入、下拉框、数值、日期与 ghost 按钮的焦点切换会改变内容矩形；修改后六类控件全部保持矩形不变。普通多行输入滚动条实测由 4px 改为 10px。
- 截图：本机临时目录 `snowfox-ui-polish/controls-{light,dark}-{before,after}.png`。
- GUI、Agent、Plan、tool hooks 与架构依赖回归（含 GLM-5.3 更正后重跑三次）：1094 passed、81 subtests passed（122.54 / 150.33 / 168.37 秒）。
- 全量 `pytest -q`：2065 passed、204 subtests passed（476.88 秒）。
- 观察到两项与本轮改动无关的偶发失败，均在单文件重跑时通过，且都不在本轮触及的路径上：`tests/unit/test_backup_validation.py::TestListAlternativeBackups::test_excludes_specified_path`（备份写入线程在 `shutil.rmtree` 期间落 `.bak` 文件，抛 `WinError 145 目录不是空的`）与 `tests/integration/plan/test_plan_executor.py::RunPlanExecuteTests::test_run_plan_move_batch_fails_marks_all_blocked`。两者不计入本轮回归结论，但属于仓库既有的测试稳定性问题。
- `ruff check .`：All checks passed；`git diff --check` 通过。
- 未发送真实付费模型请求，未重新打包安装版。

### 2026-09-23 结果会话恢复后复核

- 补跑同一模块组合：1089 passed、81 subtests passed，5 项 Bash 终端测试失败。实际调用返回 `WSL_E_DEFAULT_DISTRO_NOT_FOUND`：当前 PATH 命中了系统 WSL 启动器，但没有默认 Linux 发行版。
- 仅在测试子进程的 PATH 前置已安装的 Git Bash 后，`test_terminal_tool.py` 全部 8 passed（含前述 5 项失败测试）。未修改系统 PATH、WSL 或终端生产实现。
- `ruff check .` 与 `git diff --check` 通过。本次日志保存在系统临时目录 `snowfox-glm53-regression.log`。
