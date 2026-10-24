# STRUT's Agent

一个基于 LLM Tool Calling 的 **C 语言单元测试生成 Agent**，目标是复现 STRUT（*Structured Seed Case Guided Unit Test Generation for C Programs using LLMs*）论文的流水线。

Agent 通过对话调用工具，把「C 源文件 + 种子用例」一步步加工成给大模型的测试生成提示词，再把模型输出落盘为测试用例 JSON。

## 工作流程

```
C 源文件 ─┐
          ├─► 1. 代码简化 ─► 2. 解析种子用例 ─► 3. 生成 Prompt ─► 4. 调用模型 ─► 测试用例
种子用例 ─┘     (clang AST)      (case/PTR/stub)                    (DeepSeek)
```

1. **代码简化**：用 libclang 解析 AST，删除无函数体的声明、全局变量的赋值、未被引用的顶层定义。
2. **解析种子用例**：从 `*_seed.json` 中提取用例、`default_PTR` 和是否存在 stub。
3. **生成 Prompt**：拼装函数上下文与种子用例（uncovered 分支场景另有优化提示词模板）。
4. **调用模型**：把 Prompt 发给模型，结果写入 `cline_com/output/result.json`。

## 目录结构

| 目录 | 说明 |
| --- | --- |
| `src/agent.py` | Agent 主循环：读输入 → 调模型 → 执行 tool call → 写回记忆 |
| `src/model.py` | DeepSeek 客户端（OpenAI 兼容接口），支持普通对话与工具调用 |
| `src/message.py` | `Message` / `ToolcallMessage`，负责消息与 tool call 的转换 |
| `src/memory.py` | 对话记忆，按 OpenAI 协议写入 assistant / tool 消息 |
| `src/tool.py` | 工具定义与注册表，由函数签名自动生成 JSON Schema |
| `src/paths.py` | 统一的输出目录（`cline_com/output/`） |
| `tools/` | STRUT 算法实现：clang 静态分析、用例解析、Prompt 生成 |
| `cline_com/` | 示例输入（`circle.c` / `circle_seed.json`）与输出 |

Agent 当前注册的工具：

- `simplify(input_path, case_path, output_path=None)` — 简化 C 代码并生成提示词
- `prompt_to_model(input_prompt)` — 把提示词发给模型并保存结果

## 快速开始

要求 Python ≥ 3.12，依赖用 [uv](https://docs.astral.sh/uv/) 管理。

```bash
uv sync
```

在项目根目录的 `.env` 中配置：

```env
DEEPSEEK_API_KEY=your-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

运行 Agent：

```bash
python -m src.agent
```

输入自然语言指令后，Agent 会自行决定调用哪个工具；输入 `exit` 退出。
运行产物统一写到 `cline_com/output/`：简化后的源码、`prompt.txt`、`result.json`。

## 依赖

`clang` / `libclang`（C 代码静态分析）、`openai`（DeepSeek 兼容接口）、`python-dotenv`。
