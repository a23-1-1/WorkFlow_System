# 排查：LLM 结构化输出全 null / 空数组

当代码节点 `valid=true`，但 `result` 中 `basic` 全为 `null`、`education` / `work_experience` / `skills` 为空时，说明 **JSON 语法与 Schema 通过了代码节点校验**，但 **LLM 没有从简历中抽到有效内容**（或 LLM 根本没收到简历正文）。

> 代码节点 [`code-node-resume.py`](code-node-resume.py) 会用 `setdefault` 补全缺失字段；因此「全 null + 空数组」仍可能 `valid=true`。不能仅用 `valid` 判断提取是否成功。

---

## 一、按 Dify 运行日志逐步排查

在 Studio 或 API 调用后，打开该次运行的 **追踪（Trace）/ 日志**，按节点顺序检查。

### 步骤 1：文档提取器 — 输出是否为空

1. 展开 **文档提取器** 节点。
2. 查看输出变量（常见名：`text` 或你自定义的 `extracted_text`）。
3. **正常**：应能看到姓名、学校、公司、项目等中文段落（数百字以上常见）。
4. **异常**：
   - 输出为空字符串、`null` 或极短乱码 → docx 未解析或文件未传入。
   - 仅有文件名、无正文 → 提取失败。

**若此处已为空**：问题在文档提取器或文件上传，**不是 LLM 或代码节点**。先完成 [第三节 docx 测试](#三docx-测试方法)，再重跑。

### 步骤 2：LLM 节点 — 输入（USER 消息）是否含全文

1. 展开 **LLM** 节点 → 查看 **输入 / Prompt**（或 Messages）。
2. 找到用户消息里 `【简历原文】`（或你模板中的等价标记）**下方**的内容。
3. **正常**：与步骤 1 文档提取器输出一致的长文本。
4. **异常**：
   - `【简历原文】` 下方为空 → **用户消息未正确引用变量**（最常见配置错误之一）。
   - 仍显示 `{{#文档提取器.text#}}` 等未替换占位符 → 变量名或节点名写错。
   - 引用了 `extracted_text`，但提取器实际输出变量是 `text`（或反之）。
   - 正文只挂在 LLM **上下文（Context）**，USER 几乎为空 → 模型可能读不到简历；见下方「橙字警告」。

**对照（方案 A，推荐）**：

- **SYSTEM**：仅 [`prompt-system.txt`](prompt-system.txt)，不含简历变量。
- **USER**：全文 [`prompt-user-template.txt`](prompt-user-template.txt)，`【简历原文】` + 正确 `{{#节点.变量#}}`。
- **上下文**：留空，不添加文档提取器变量。

操作清单：[`dify-llm-setup-plan-a.md`](dify-llm-setup-plan-a.md)。

#### 橙字「要启用上下文功能…」

Dify 在 LLM 节点 **上下文** 区域引用变量但未正确启用上下文时，可能出现橙色提示：**「要启用上下文功能，请在提示词中引用上下文变量」**。

| 做法 | 说明 |
|------|------|
| **推荐：改用方案 A** | USER 粘贴 [`prompt-user-template.txt`](prompt-user-template.txt)（含 `{{#文档提取器.text#}}`），**上下文留空**。Trace 中检查 `【简历原文】` 下有真实正文即可。 |
| **备选：坚持走上下文** | 必须在 **USER 或 SYSTEM** 中显式引用上下文变量（如 `{{#context#}}` 或你版本中的等价写法），并同时保证 Trace 里模型能读到完整简历；仅挂上下文、USER 无正文时仍易全 null。 |

**不要** 只在上下文拖入 `text` 而 USER 为空——这与本仓库默认 **方案 A** 不符，也是「输入有字、输出仍空」的常见原因。

### 步骤 3：LLM 节点 — 输出是否为「空 Schema」

1. 查看 LLM **输出**（结构化 JSON 或 text）。
2. 若输入已有完整正文，但输出仍全 `null` / `[]`（**输入有字、输出仍空**）：
   - 换用仓库最新 [`prompt-system.txt`](prompt-system.txt) + [`prompt-user-template.txt`](prompt-user-template.txt)，确认禁止「有正文时四项核心字段同时全空」。
   - 若已开 **JSON Schema / 结构化输出**，模型仍须读 USER 全文；可暂时关闭纯结构化约束或换模型后重试。
   - 检查 **温度** 或 **max tokens** 是否导致截断（长简历需足够 token）。
   - 检查 **结构化输出 Schema** 是否与提示词字段一致（可选 `error` 字段需在 Schema 中声明）。
3. 若 LLM 输出含 `error` 字段 → 模型判定未收到正文，回到步骤 1、2。

### 步骤 4：代码节点 — 区分「解析成功」与「提取成功」

1. 展开 **代码** 节点，确认输入 `llm_raw_output` 与 LLM 输出一致。
2. `valid=true` 仅表示：输入是合法 JSON 且规范化成功。
3. **业务成功** 建议额外判断，例如：
   - `basic.name` 非空，或
   - `len(education) + len(work_experience) > 0`，或
   - LLM 输出无 `error` 字段。

可在结束节点或下游增加条件分支，避免将「空简历 JSON」当作成功结果返回。

---

## 二、根因对照表

| 现象 | 最可能根因 | 处理 |
|------|------------|------|
| 文档提取器 `text` 为空 | docx 损坏、加密、上传失败、未连接开始节点 `resume_file` | 换 txt 测通链路；检查文件输入连线 |
| 提取器有字，LLM USER 为空 | 用户消息未引用 `{{#文档提取器.text#}}` 或变量名错误；或正文只挂在「上下文」 | 按 **方案 A**：USER 用 `prompt-user-template.txt`，上下文留空；见 [`dify-llm-setup-plan-a.md`](dify-llm-setup-plan-a.md) |
| LLM 橙字「要启用上下文功能…」 | 上下文引用了变量但未在提示词中引用，或配置与方案 A 混用 | 改用方案 A（USER 含 `{{#文档提取器.text#}}`，上下文留空）；或必须在 USER/SYSTEM 引用上下文变量 |
| USER 有字，输出仍全 null | 提示词过旧；或结构化输出下模型未读正文、用全 null 糊弄 | 更新 `prompt-system.txt` + `prompt-user-template.txt`；可关结构化输出后重试 |
| 偶发全 null | 模型/context 限制、超长简历截断 | 换模型、增大 max tokens、截断前 N 字再传入 |

---

## 三、docx 测试方法

按以下顺序隔离问题（勿使用含真实 PII 的文件提交到 Git）。

### 3.1 最小链路测试（推荐）

1. 将同一份 docx **另存为 `.txt`**（UTF-8），在开始节点用 `resume_text` 粘贴全文，**绕过文档提取器**。
2. LLM 用户消息改为：`{{#开始.resume_text#}}`。
3. 若 txt 路径能抽出字段 → 问题在 **docx 解析 / 文档提取器**。
4. 若 txt 路径仍全 null → 问题在 **LLM 提示词或变量引用**。

### 3.2 仅测文档提取器

1. 工作流中暂时只保留：开始 → 文档提取器 → 结束（结束节点输出 `text`）。
2. 上传 `示例-数据开发-简历.docx`（或你的样例）。
3. 看结束输出是否含「张某某」、学校、项目等关键词。

### 3.3 docx 常见问题

| 情况 | 说明 |
|------|------|
| 复杂表格 / 文本框 | 部分 docx 提取器只能读正文流，表格内文字可能丢失 |
| 扫描件式 docx | 实为图片嵌入，无 OCR 则无文字 |
| 文件名含特殊字符 | 一般不影响内容，但应以提取器输出为准 |
| Dify 版本差异 | 输出变量默认可能是 `text` 而非 `extracted_text` |

### 3.4 快速本地查看 docx 正文（可选）

在本地用 Word / WPS 打开，或解压 docx 查看 `word/document.xml` 是否有可读文本（开发机操作，勿把真实简历提交仓库）。

---

## 四、应届数据开发类简历提取提示

针对如 `示例-数据开发-简历.docx` 这类**校招 / 数据开发**简历，LLM 应重点扫描以下区块（原文有什么抽什么，不要臆造）：

| 区块 | 常见位置 / 关键词 | 映射字段 |
|------|-------------------|----------|
| 个人信息 | 姓名「张某某」、手机、邮箱、意向城市 | `basic.*` |
| 教育背景 | 「2024届」、本科/硕士、院校、专业、数据/计算机相关 | `education[]` |
| 实习 / 项目 | 公司或项目组、「数据开发」「ETL」「数仓」 | `work_experience[]`（实习可写入 company） |
| 技能栈 | Hadoop、Spark、Hive、Flink、SQL、Python、Linux | `skills[]` |
| 自我评价 | 段落首句职业定位 | `summary` |

**注意：**

- 「2024届」通常表示毕业年份，可写入 `education[].end_date` 或辅助判断 `years_of_experience`（应届多为 `0` 或 `null`）。
- 项目经历若未写公司名，可用项目组或课程项目名称填入 `work_experience[].company`，并在 `description` 中保留技术细节。
- 若原文确有「张某某」但 JSON 中 `name` 仍为 null → 几乎可断定 LLM **未看到正文**，回到第一节步骤 1–2。

---

## 五、推荐修复清单（Dify 界面 · 方案 A）

- [ ] 文档提取器已连接 `resume_file`，且 Trace 中 `text` 非空
- [ ] LLM **SYSTEM** 仅 [`prompt-system.txt`](prompt-system.txt)，**不含**简历 `{{#...#}}`
- [ ] LLM **USER** 已粘贴最新 [`prompt-user-template.txt`](prompt-user-template.txt)，含 `【简历原文】` + 正确 `{{#节点.变量#}}`
- [ ] LLM **上下文** 留空，未添加文档提取器变量（无橙字警告）
- [ ] Trace 自检：`【简历原文】` 下方为真实正文（非占位符）
- [ ] 系统提示词已替换为最新 [`prompt-system.txt`](prompt-system.txt)
- [ ] 结构化输出 Schema 与提示词字段一致（若启用 `error` 字段，需在 Schema 中增加 optional `error`）
- [ ] 代码节点后增加条件：`name` 非空或 `education`/`work_experience` 非空再视为成功
- [ ] 用 txt 绕过提取器做一次对照实验

---

## 六、相关文档

- 工作流搭建：[`dify-workflow.md`](dify-workflow.md)
- 方案 A 操作清单：[`dify-llm-setup-plan-a.md`](dify-llm-setup-plan-a.md)
- 系统提示：[`prompt-system.txt`](prompt-system.txt)；用户模板：[`prompt-user-template.txt`](prompt-user-template.txt)
- 代码节点：[`code-node-resume.py`](code-node-resume.py)
- 输出 Schema：[`../examples/schema-resume.json`](../examples/schema-resume.json)
