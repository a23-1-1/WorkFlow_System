# 方案 A：LLM 节点配置清单

本仓库 **默认推荐** 方案 A：简历正文 **只通过 USER 传入**，SYSTEM 不含变量，LLM「上下文」留空。

---

## 三步操作（Dify 界面）

| 步骤 | 位置 | 操作 |
|------|------|------|
| 1 | **SYSTEM / 系统提示词** | 粘贴 [`prompt-system.txt`](prompt-system.txt) **全文**（勿加 `{{#...#}}`） |
| 2 | **USER / 用户消息** | 粘贴 [`prompt-user-template.txt`](prompt-user-template.txt) **全文**；确认 `【简历原文】` 下一行为 `{{#文档提取器.text#}}`（或与你画布一致的占位符） |
| 3 | **上下文（Context）** | **留空** — 不添加文档提取器或任何变量 |

---

## 变量名对照

| 画布情况 | USER 中占位符 |
|----------|----------------|
| 文档提取器输出 `text`（默认） | `{{#文档提取器.text#}}` |
| 输出改名为 `extracted_text` | `{{#文档提取器.extracted_text#}}` |
| 节点名不是「文档提取器」 | 改为 `{{#你的节点名.text#}}` |
| 绕过提取器，用开始节点 `resume_text` | `{{#开始.resume_text#}}` |

语法以当前 Dify 版本为准，常见为 `{{#节点名.变量名#}}`。

---

## Trace 自检（必做）

1. Studio 运行一次（上传样例简历）。
2. 打开 **追踪** → 展开 **LLM** → 查看 **USER** 消息。
3. 找到 `【简历原文】` → **下方必须是真实中文段落**（姓名、学校、项目等），不能是空、不能仍是 `{{#文档提取器.text#}}`。

若此处为空 → 回到步骤 2 检查占位符与节点名；若文档提取器本身无字 → 先查 [`troubleshooting-empty-output.md`](troubleshooting-empty-output.md) 第一节。

---

## 不要做的事

- 不要把 [`prompt-user-template.txt`](prompt-user-template.txt) 贴到 SYSTEM。
- 不要在「上下文」里单独挂 `text` 而 USER 留空（易触发橙字「要启用上下文功能…」，且易全 null）。
- 不要在 SYSTEM 里引用 `{{#文档提取器.text#}}`（与方案 A 设计不符）。

---

## 相关文档

- 完整搭建：[`dify-workflow.md`](dify-workflow.md) 第四节  
- 全 null / 橙字排查：[`troubleshooting-empty-output.md`](troubleshooting-empty-output.md)
