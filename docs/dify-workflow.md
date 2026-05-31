# Dify 简历提取工作流 — 详细搭建步骤

本文档按节点顺序说明如何在 Dify **工作流（Workflow）** 应用中搭建简历信息提取器。界面文案可能随 Dify 版本略有差异，以你当前控制台为准。

---

## 一、创建应用

1. 登录 Dify 控制台（云版或自托管）。
2. 点击 **创建应用** → 选择 **工作流（Workflow）**。
3. 应用名称建议：`简历结构化提取`；描述中注明「仅处理招聘场景简历文本」。

---

## 二、开始节点（Start）

### 配置

| 配置项 | 建议 |
|--------|------|
| 输入变量 `resume_file` | 类型：文件；允许 `pdf`、`docx`、`txt` |
| 可选变量 `resume_text` | 类型：文本；用于已粘贴的纯文本简历 |
| 说明文案 | 提醒用户勿上传含敏感附件的压缩包 |

### 逻辑

- 若用户上传文件，后续走 **文档提取器**。
- 若仅提供 `resume_text`，可跳过文档提取器，直接将文本传入 LLM（需在画布上用 **条件分支** 或统一在代码节点里合并变量）。

---

## 三、文档提取器（Document Extractor）

### 作用

将 PDF / Word 等转为可供 LLM 阅读的纯文本。

### 配置步骤

1. 从节点面板拖入 **文档提取器**（或「文档」类节点）。
2. 将 **开始** 节点的 `resume_file` 连接到文档提取器的文件输入。
3. 输出变量：Dify 默认常为 **`text`**；若重命名为 `extracted_text`，LLM 用户消息中的 `{{#...#}}` 必须与此**完全一致**。
4. 在节点说明中注明：扫描版 PDF 若无 OCR 可能提取失败；复杂 docx 表格/文本框可能提取不全。

### 调试

- 使用一份 **无真实 PII** 的样例 PDF / docx / txt 在 Studio 运行。
- 在 **追踪** 中展开文档提取器，确认 `text`（或 `extracted_text`）**非空**且含姓名、教育、项目等段落。
- 若 docx 提取为空，见 [`troubleshooting-empty-output.md`](troubleshooting-empty-output.md) 第三节「docx 测试方法」。

---

## 四、LLM 节点 — 结构化输出

> **默认推荐：方案 A**（简历正文只走 USER，上下文留空）。三步清单见 [`dify-llm-setup-plan-a.md`](dify-llm-setup-plan-a.md)。

### 模型选择

- 优先选择支持 **JSON / 结构化输出** 的模型。
- **温度**：0 ~ 0.3，降低随意发挥。
- **最大 Token**：按简历平均长度上调，避免截断。

### 方案 A（推荐）：只配 SYSTEM + USER

本仓库 **默认采用方案 A**：简历正文 **唯一** 通过 USER 传入；SYSTEM 仅放规则与 Schema；**不** 在 LLM「上下文（Context）」挂文档提取器。

| 区域 | 粘贴内容 | 是否引用简历变量 |
|------|----------|------------------|
| **SYSTEM** | 仅 [`prompt-system.txt`](prompt-system.txt) 全文 | **否** — 不含任何 `{{#...#}}` |
| **USER** | [`prompt-user-template.txt`](prompt-user-template.txt) 全文 | **是** — `【简历原文】` 下一行引用提取器 |
| **上下文（Context）** | **留空**；若曾添加过变量请 **删除** | **否** — 避免橙字警告与全 null |

#### 界面操作（截图式步骤 · 中文）

**第 1 步 — 配置 SYSTEM**

1. 双击画布上的 **LLM** 节点，打开右侧配置面板。
2. 找到 **SYSTEM / 系统提示词** 大文本框（通常在 USER 上方）。
3. 打开本仓库 [`prompt-system.txt`](prompt-system.txt)，**Ctrl+A 全选 → 复制 → 粘贴** 到 SYSTEM 框。
4. 检查 SYSTEM 内 **没有** `{{#文档提取器.text#}}` 等变量占位符 → 点击 **保存**。

**第 2 步 — 配置 USER（必做，不可省略）**

1. 在同一 LLM 面板，切换到 **USER / 用户消息** 输入框。
2. 打开 [`prompt-user-template.txt`](prompt-user-template.txt)，**全文粘贴**（含顶部「仅粘贴到 USER」说明与文末配置提醒）。
3. 向下滚动，找到 **`【简历原文】`** 标记 → 其 **紧下一行** 必须是：
   ```text
   {{#文档提取器.text#}}
   ```
   （节点名或输出变量改名时，只改这一行占位符，与 Trace 里文档提取器实际变量名一致。）
4. **不要** 只在「上下文」里加 `text` 而 USER 留空——模型 Trace 中 USER 无正文时会输出全 `null`，代码节点仍可能 `valid=true`。
5. 保存 LLM 节点。

**第 3 步 — 上下文留空或删除已有变量**

1. 在 LLM 配置中找到 **上下文（Context）** 折叠区并展开。
2. **正确**：列表为空，未添加任何上游变量。
3. **若曾添加** 文档提取器的 `text` / `extracted_text`：点击变量右侧 **删除（×）**，直到上下文为空。
4. 保存后，面板 **不应** 再出现橙字：**「要启用上下文功能，请在提示词中引用上下文变量」**。

**第 4 步 — Trace 自检**

1. Studio 上传样例简历 → **运行**。
2. 打开 **追踪（Trace）** → 展开 **LLM** → 查看 **USER** 消息。
3. 定位 `【简历原文】` → **下方必须是真实中文段落**（姓名、学校、项目等），不能是空，不能仍是未替换的 `{{#...#}}`。
4. 若 USER 有正文但 JSON 仍全 null → 见 [`troubleshooting-empty-output.md`](troubleshooting-empty-output.md)。

#### 变量名对照（只改 USER 中一行）

| 场景 | USER 中 `【简历原文】` 下占位符 |
|------|--------------------------------|
| 提取器输出 `text`（默认） | `{{#文档提取器.text#}}` |
| 输出改名为 `extracted_text` | `{{#文档提取器.extracted_text#}}` |
| 仅文本输入 `resume_text` | `{{#开始.resume_text#}}` |

#### 橙字警告原因（简要）

| 现象 | 原因 | 处理 |
|------|------|------|
| 橙字「要启用上下文功能…」 | 上下文已挂变量，但 USER/SYSTEM **未** 引用上下文变量 | **方案 A**：删除上下文变量，正文只放 USER（推荐） |
| `valid=true` 但全 null | 只在上下文加了 `text`，USER 无 `【简历原文】` 正文 | 按第 2 步粘贴 [`prompt-user-template.txt`](prompt-user-template.txt) |
| Trace 中 USER 为空 | USER 未引用 `{{#文档提取器.text#}}` 或占位符写错 | 对照上表修改变量名后重跑 |

> **禁止的配置**：只配 SYSTEM + 结构化输出 Schema + 上下文挂 `text`，**USER 为空** → 最常见「输入有字（在上下文）、输出全 null」故障。方案 A 要求 USER 含 `【简历原文】` + 变量，上下文留空。

> 变量语法以 Dify 当前版本为准，常见为 `{{#节点名.变量名#}}`。开启 JSON Schema 时模型仍须阅读 USER 全文，不可用全 null 通过校验。

### 输出

- **推荐**：若 LLM 节点已开启 **结构化输出 / JSON Schema**，将结构化结果映射为变量（如 `structured_output` 或节点自带的 JSON 字段），在代码节点中绑定为 `llm_raw_output`（见第五节）。
- **备选**：若仅使用文本输出，将 LLM 的 **text** 映射并在代码节点绑定为 `llm_raw_output`；不要在提示词中要求返回 Markdown 代码块。若模型仍返回 \`\`\`json，代码节点会自动剥离。

---

## 五、代码节点（云端 Python3）— JSON 校验与规范化

### 目的

- 支持 `llm_raw_output` 为 **dict/object**（结构化输出，直接使用）或 **str**（剥离 Markdown 围栏后 `json.loads`）
- 对顶层与子字段做 `setdefault` 补全，`skills` 去重
- 邮箱简单正则校验（无效时保留原文并标记 `basic._email_invalid`）
- 手机号归一化（去非数字、大陆 11 位取后 11 位；国际号/座机见代码注释局限）

### 完整代码

将仓库内 [`code-node-resume.py`](code-node-resume.py) **全文复制**到 Dify 代码节点，勿遗漏 `import` 与 `main` 函数。

### 输入变量名必须与 `main()` 参数名一致（重要）

Dify 会把代码节点「输入变量」列表里的 **每一个变量名** 作为 **keyword 参数** 传给 `main()`。例如界面配置了 `llm_raw_output` 和 `arg2`，运行时等价于：

```python
main(llm_raw_output=..., arg2=...)
```

若 `main()` 未声明 `arg2`，会报错：

```text
TypeError: main() got an unexpected keyword argument 'arg2'
```

**推荐做法：**

| 项 | 说明 |
|----|------|
| 只保留一个输入变量 | 变量名 **`llm_raw_output`**，与 `main(llm_raw_output=None, **kwargs)` 一致 |
| 删除未使用变量 | 删除 **`arg2`** 及任何未在 `main()` 中声明的占位变量 |
| 结构化输出 | 绑定 LLM 的 **JSON / object** 字段，**不要**再绑 text |
| 纯文本输出 | 绑定 LLM 的 **text** 到 `llm_raw_output` |

当前代码使用 `**kwargs` 吸收多余入参，避免偶发残留变量导致崩溃，但 **仍应在 Dify 界面删除 `arg2`**，以免传入无意义数据。

### 在 Dify 中配置

| 项 | 说明 |
|----|------|
| 节点类型 | **代码**，语言选 **Python 3**（云端） |
| 输入变量 `llm_raw_output` | 绑定上一 **LLM** 节点的 **结构化 JSON 输出**（优先）或 **text** |
| 输出变量 `valid` | 布尔：`true` 表示 JSON 解析与规范化成功 |
| 输出变量 `result` | 字符串：规范化后的 JSON（`ensure_ascii=False`，中文不转义） |
| 输出变量 `error` | 字符串：失败原因；成功时为空字符串 |

配置步骤：

1. 从节点面板拖入 **代码** 节点，接在 LLM 节点之后。
2. 在「输入变量」**仅**新增 `llm_raw_output`：
   - LLM 已开结构化输出 → 选择该节点的 **JSON / structured_output**（名称以控制台为准）；
   - 否则 → 选择 `LLM.text`。
3. **检查并删除** `arg2` 等未使用输入变量（见下方排查）。
4. 在「输出变量」声明 `valid`（布尔）、`result`（字符串）、`error`（字符串）。
5. 将 [`code-node-resume.py`](code-node-resume.py) 全部粘贴到代码编辑区并保存。

### 常见错误：`unexpected keyword argument 'arg2'`

**根因：** 代码节点输入区存在变量名 `arg2`（常为 Dify 默认占位或未删干净的测试变量），但旧版 `main()` 只接受 `llm_output` 等固定参数。

**排查步骤（中文）：**

1. 打开报错的 **代码** 节点 → **输入变量** 列表。
2. 查看是否除 `llm_raw_output` 外还有 **`arg2`、`arg1`、`input` 等** 未使用项。
3. 点击 **删除** 所有与 `main()` 无关的变量；只保留 `llm_raw_output`。
4. 确认 `llm_raw_output` 已正确绑定上游 LLM（结构化 JSON 或 text，二选一）。
5. 将仓库最新 [`code-node-resume.py`](code-node-resume.py) 全文粘贴覆盖节点代码（含 `def main(llm_raw_output=None, **kwargs)`）。
6. 保存后在 Studio 重新运行；用示例输入 `{ "basic": { "name": null, ... } }` 验证 `valid=true`。

### 条件分支与失败重试（简述）

解析失败时不应直接把脏数据交给结束节点，建议在代码节点后增加 **条件分支**：

- **若** `valid` 为 `true` **且** 提取结果非空（例如 `basic.name` 非 null，或 `education` / `work_experience` 至少一项）→ 连接 **结束** 节点，将 `result` 作为业务输出。
- **若** `valid` 为 `true` 但字段全空 → 视为 **提取失败**（LLM 未收到正文或未抽取），返回错误说明，见 [`troubleshooting-empty-output.md`](troubleshooting-empty-output.md)。
- **若** `valid` 为 `false` → 可选路径：
  - 将 `error` 写入结束节点的错误字段，直接返回给调用方；
  - 或接回 **LLM** 节点重试（在提示词中附带 `error` 与上一轮输出，要求仅输出修正后的 JSON），并限制最大重试次数以防循环。

Studio 调试时可故意让模型返回带 \`\`\`json 围栏或缺字段的文本，确认 `valid=false` 与 `error` 文案符合预期。

---

## 六、展示代码节点（中文标签，可选但推荐）

解析代码节点输出的 `result` 为英文 snake_case JSON，适合 API 入库；**最终用户**更适合阅读中文 Markdown。

### 目的

- `result` 保持英文 JSON 不变（业务 / 集成）
- 新增 `display_markdown`：分段中文 + 表格，供 Web App / 聊天展示
- 可选 `display_json`：中文键名的 JSON 字符串

### 在 Dify 中配置

1. 在 **简历解析** 代码节点之后，再拖入一个 **代码** 节点（可命名为「中文展示」）。
2. **输入变量**：仅 `result`，绑定 **上一代码节点** 的 `result`。
3. **输出变量**：`valid`（布尔）、`result`（字符串）、`display_markdown`（字符串）、`display_json`（字符串）、`error`（字符串）。
4. 将 [`code-node-display-zh.py`](code-node-display-zh.py) **全文复制**到该节点并保存。
5. 条件分支成功路径应连接到 **展示代码节点**，再由展示节点连到 **结束** 节点。

详细三种方案对比与示例输出见 [`display-chinese-labels.md`](display-chinese-labels.md)。

### 连线示意

```text
LLM → 代码（code-node-resume.py）→ [条件分支 valid=true] → 代码（code-node-display-zh.py）→ 结束
```

---

## 七、结束节点与变量输出

1. 经条件分支（见第五节）将成功路径连接到 **展示代码节点**（若已配置）或直连 **结束** 节点。
2. 在「输出变量」中暴露，例如：

| 暴露名 | 绑定来源 | 说明 |
|--------|----------|------|
| `valid` | 解析代码节点 `valid` | 业务是否解析成功 |
| `error` | 解析或展示节点 `error` | 错误信息 |
| `resume_json` | 展示节点 `result`（或无展示节点时用解析节点 `result`） | 英文 JSON 字符串 |
| `display_markdown` | 展示节点 `display_markdown` | **给用户看**的中文 Markdown |
| `display_json` | 展示节点 `display_json` | 中文键 JSON（可选） |

- Web App：**默认回复 / 结束输出** 优先绑 `display_markdown`。
- HTTP API：同时返回 `resume_json` 与 `display_markdown`，由调用方选择展示方式。

便于 API 调用方根据 `valid` 判断业务是否成功。

---

## 八、测试清单（Studio）

- [ ] 上传短 TXT 简历，JSON 可解析
- [ ] 上传多页 PDF，教育/工作经历未大面积丢失
- [ ] 故意缺少「工作经历」的文本，观察 LLM 输出经代码节点后 `valid` 与 `result` 是否仍可用（缺字段由 `setdefault` 补全）
- [ ] 无效邮箱或带 +86 的手机号，确认 `_email_invalid` 标记与手机归一化结果
- [ ] 模型返回带 \`\`\`json 围栏时，代码节点仍能解析
- [ ] 展示代码节点 `display_markdown` 含「基本信息」「教育背景」等中文标题，无英文 snake_case 键名外露

---

## 九、发布 API

1. 进入应用 **发布** → 生成 **API 访问**。
2. 在 **API 密钥** 中创建 Key，复制到本机 `.env`：

```env
DIFY_API_KEY=your_key_here
DIFY_BASE_URL=https://api.dify.ai/v1
```

3. 记录工作流 **端点 URL** 与 **输入参数名**（与开始节点一致）。
4. 使用 Postman 或 `curl` 做 blocking 调用测试。

### 安全建议

- API Key 仅服务端持有，禁止前端暴露
- 对上传文件做大小、类型白名单
- 记录请求 ID 便于排查，日志中避免打印完整简历正文

---

## 十、常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `valid=true` 但 JSON 全 null / 空数组 | 文档提取器 `text` 为空；或 LLM 用户消息未引用 `{{#文档提取器.text#}}`；或仅有 system 无正文 | 按 [`troubleshooting-empty-output.md`](troubleshooting-empty-output.md) 逐步查 Trace |
| `TypeError: ... unexpected keyword argument 'arg2'` | 代码节点输入区留有 `arg2` 等未声明变量 | 删除多余输入变量，仅保留 `llm_raw_output`；见第五节排查 |
| 提取结果为空 | 扫描 PDF、加密 PDF、docx 表格/文本框 | 改 txt 测链路；要求可选中文本的文件 |
| JSON 经常失败 | 温度过高、未约束仅 JSON | 降低温度，强化系统提示词 |
| 字段幻觉 | 原文无该项 | 提示词要求「无则 null 或 []」 |
| Token 超限 | 简历过长 | 代码节点截断 `extracted_text` 前 N 字符 |

---

## 十一、与本仓库文件的对应关系

| 文件 | 用途 |
|------|------|
| `prompt-system.txt` | LLM **系统** 提示词（全文粘贴到 SYSTEM，不含简历变量） |
| `prompt-user-template.txt` | LLM **用户消息**模板（全文粘贴到 USER，含 `【简历原文】`） |
| `dify-llm-setup-plan-a.md` | 方案 A 三步操作清单 |
| `troubleshooting-empty-output.md` | 全 null / 空数组排查（docx、变量引用、Trace） |
| `code-node-resume.py` | 云端 Python3 解析代码节点全文（复制粘贴） |
| `code-node-display-zh.py` | 云端 Python3 **中文展示**代码节点全文（接在解析节点之后） |
| `display-chinese-labels.md` | 中文标签三种展示方案与示例 |
| `../examples/schema-resume.json` | 字段说明与类型约定 |
| `../examples/labels-zh.json` | 字段路径 → 中文标签映射 |
| `../examples/output-sample.json` | 虚构脱敏输出样例 |

完成搭建后，可将本仓库链接写在个人 README 或学习笔记中，**勿提交真实简历与密钥**。
