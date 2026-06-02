# 招聘初筛二期 7 天执行计划

本文档给出「AI 招聘初筛与面试助手」二期工作流的 7 天落地计划。目标是每天都有可验证产出，避免一次改太多难以定位问题。

## Day 1：JD 结构化提取跑通

### 当日目标

- 新增岗位 JD 提取节点（LLM + 代码校验）。
- 能把一段 JD 文本稳定提取为 JSON。

### Dify 操作

1. 在 Start 节点增加 `jd_text`（文本）。
2. 新增 `LLM_JD提取`：
   - SYSTEM：`docs/prompt-jd-extraction.txt`
   - USER：`docs/prompt-jd-user-template.txt`
3. 新增代码节点，粘贴：`docs/code-node-jd-parse.py`
4. End 节点输出 `jd_json`（绑定代码节点 `result`）。

### 验收标准

- Trace 中 LLM 输入包含 `【岗位原文】`。
- `valid=true` 且 `jd_json` 至少包含 `job_title` 和 `required_skills`。

### 常见坑

- USER 未引用 `jd_text`，导致全空。
- 代码节点参数名与输入变量不一致，触发 unexpected keyword argument。

## Day 2：简历与 JD 双通道并联

### 当日目标

- 复用一期简历提取链路。
- 同一次运行拿到 `resume_json` 与 `jd_json`。

### Dify 操作

1. 保留一期链路：文档提取器_resume → LLM_简历 → `code-node-resume.py`。
2. 并联 Day 1 的 JD 链路。
3. 在 End 节点同时输出 `resume_json` 和 `jd_json`。

### 验收标准

- 同一 Trace 中两个 JSON 都可解析。
- 任一侧失败时可通过 `error` 明确定位。

### 常见坑

- 变量重名（例如两个节点都叫 `text` 且引用错）。
- End 节点只输出了一个分支结果。

## Day 3：匹配评分能力

### 当日目标

- 基于 `resume_json` + `jd_json` 生成匹配评分。
- 分数与建议可被机器读取。

### Dify 操作

1. 新增 `LLM_匹配评分`：
   - SYSTEM：`docs/prompt-match-score.txt`
   - USER：`docs/prompt-match-user-template.txt`
2. 新增代码节点，粘贴：`docs/code-node-match-normalize.py`
3. 输出 `match_json`。

### 验收标准

- `match_score` 在 0–100。
- `recommendation` 属于：`strong_recommend`/`recommend`/`hold`/`reject`。
- `matched_points`、`missing_points` 非空（至少一项）。

### 常见坑

- LLM 给出 105 或 -5 分，未做归一化。
- recommendation 文本值不在枚举内。

## Day 4：面试题生成

### 当日目标

- 从匹配结果自动生成技术面试题与追问题。

### Dify 操作

1. 新增 `LLM_面试题生成`：
   - SYSTEM：`docs/prompt-interview-questions.txt`
   - USER：`docs/prompt-interview-user-template.txt`
2. 输出 `interview_questions_json`。

### 验收标准

- 技术题 >= 3。
- 项目题 >= 2。
- 风险追问 >= 1。

### 常见坑

- 问题过于泛化（例如「请自我介绍」重复出现）。
- 与 JD 无关的问题占比过高。

## Day 5：条件分支与错误处理

### 当日目标

- 低分候选人走不同输出模板。
- 任一上游失败可优雅返回。

### Dify 操作

1. 新增分支：`match_score >= 70` 与 `< 70`。
2. 新增错误分支：任一 `valid=false` 直接结束并返回 `error`。
3. 在 End 输出加入 `valid` 与 `error`。

### 验收标准

- 低分时输出「暂不推荐」并附缺失项。
- 上游失败时不再继续跑后续高成本节点。

### 常见坑

- 分支条件写错（字符串比较导致逻辑异常）。
- 错误分支输出字段不完整。

## Day 6：中文展示层

### 当日目标

- 给业务方提供中文可读报告，不暴露英文键名。

### Dify 操作

1. 在匹配或面试题后添加展示代码节点：
   - 复用：`docs/code-node-display-zh.py`
   - 或按 `docs/display-chinese-labels.md` 增加二期字段渲染
2. End 暴露 `display_markdown`。

### 验收标准

- 页面显示中文标题（基本信息、匹配亮点、风险点、面试题）。
- 同时保留 `match_json` 供 API 使用。

### 常见坑

- 只输出 Markdown，丢失机器可读 JSON。
- 中文展示节点没接入最新分支结果。

## Day 7：联调、回归与发布准备

### 当日目标

- 跑通端到端样例并完善文档。
- 准备发布与交付。

### Dify 操作

1. 使用虚构样例回归：
   - JD：`examples/jd-sample.json`
   - 简历：`examples/output-sample.json` 风格
2. 校验输出字段与 Schema 一致：
   - `examples/schema-jd.json`
   - `examples/schema-match-result.json`
   - `examples/schema-interview-questions.json`
3. 补齐 README 与工作流说明。

### 验收标准

- 全链路无报错，返回 JSON 可直接 `JSON.parse`。
- 中文展示可直接给业务方评审。
- 文档可让新同事在 1 小时内复现。

### 常见坑

- 示例里混入真实 PII。
- 只测成功样例，未测低分/异常分支。

## 每日通用检查清单

- SYSTEM 与 USER 是否分离。
- USER 是否包含原文变量（方案 A）。
- 上下文（Context）是否为空或明确被引用。
- 代码节点输入变量名是否与 `main()` 参数一致。
- 输出是否同时包含 JSON（机器）与 Markdown（人类）。

## 完成定义（Definition of Done）

- 文档齐全：工作流、提示词、Schema、代码节点说明、7 天计划。
- 虚构样例通过端到端测试。
- 不含真实简历、真实姓名、完整手机号、真实邮箱。
