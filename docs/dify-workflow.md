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
3. 输出变量命名建议：`extracted_text`。
4. 在节点说明中注明：扫描版 PDF 若无 OCR 可能提取失败，需用户改用可选文本的 PDF。

### 调试

- 使用一份 **无真实 PII** 的样例 PDF（或 txt）在 Studio 运行。
- 检查输出是否包含关键段落（教育、工作经历）。

---

## 四、LLM 节点 — 结构化输出

### 模型选择

- 优先选择支持 **JSON / 结构化输出** 的模型。
- **温度**：0 ~ 0.3，降低随意发挥。
- **最大 Token**：按简历平均长度上调，避免截断。

### 提示词

- **系统提示词**：复制仓库内 [`prompt-system.txt`](prompt-system.txt) 全文。
- **用户消息**：模板示例：

```text
请根据以下简历原文，严格按系统提示中的 JSON Schema 提取信息并输出 JSON。

【简历原文】
{{#extracted_text#}}
```

若使用条件分支仅文本输入，将 `extracted_text` 替换为 `resume_text`。

> 变量引用语法以 Dify 当前版本为准，常见为 `{{#节点名.变量名#}}`。

### 输出

- 将 LLM 的 **文本输出** 映射为变量 `llm_raw_output`。
- 不要在提示词中要求返回 Markdown 代码块；若模型仍返回 \`\`\`json，在下一步代码节点中剥离。

---

## 五、代码节点 — JSON 校验与规范化

### 目的

- 解析 JSON，捕获格式错误
- 校验必填字段（如 `basic`、`work_experience`）
- 可选：截断过长字段、统一日期格式

### 示例逻辑（Python）

```python
import json
import re

def main(llm_raw_output: str) -> dict:
    text = (llm_raw_output or "").strip()
    # 去掉可能的 markdown 围栏
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON 解析失败: {e}",
            "data": None,
        }

    required = ["basic", "education", "work_experience", "skills"]
    missing = [k for k in required if k not in data]
    if missing:
        return {
            "success": False,
            "error": f"缺少字段: {', '.join(missing)}",
            "data": data,
        }

    return {"success": True, "error": None, "data": data}
```

### 在 Dify 中

1. 添加 **代码** 节点，语言选 Python 3。
2. 输入：`llm_raw_output`（来自 LLM 节点）。
3. 输出：`success`、`error`、`data`（类型与控制台要求一致）。

---

## 六、结束节点与变量输出

1. 将代码节点的 `data` 连接到 **结束** 节点。
2. 在「输出变量」中暴露：
   - `success`（布尔）
   - `error`（字符串，可空）
   - `resume_json`（对象，即 `data`）

便于 API 调用方判断业务是否成功。

---

## 七、测试清单（Studio）

- [ ] 上传短 TXT 简历，JSON 可解析
- [ ] 上传多页 PDF，教育/工作经历未大面积丢失
- [ ] 故意缺少「工作经历」的文本，观察 `success=false` 与 `error` 文案
- [ ] 模型返回带 \`\`\`json 围栏时，代码节点仍能解析

---

## 八、发布 API

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

## 九、常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 提取结果为空 | 扫描 PDF、加密 PDF | 要求用户提供可选中文本的 PDF |
| JSON 经常失败 | 温度过高、未约束仅 JSON | 降低温度，强化系统提示词 |
| 字段幻觉 | 原文无该项 | 提示词要求「无则 null 或 []」 |
| Token 超限 | 简历过长 | 代码节点截断 `extracted_text` 前 N 字符 |

---

## 十、与本仓库文件的对应关系

| 文件 | 用途 |
|------|------|
| `prompt-system.txt` | LLM 系统提示词 |
| `schema-resume.json` | 字段说明与类型约定 |
| `output-sample.json` | 虚构脱敏输出样例 |

完成搭建后，可将本仓库链接写在个人 README 或学习笔记中，**勿提交真实简历与密钥**。
