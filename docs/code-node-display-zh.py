"""
Dify 云端 Python3 代码节点 — 简历 JSON 中文展示

用法：接在「简历解析」代码节点（code-node-resume.py）之后，单独新建一个代码节点。

输入变量名（必须与 main() 参数名一致）：
  result — 绑定上一代码节点的 result（规范化后的 JSON 字符串）

输出变量名：
  result          — 原样透传英文 JSON 字符串（供 API / 入库）
  display_markdown — 中文 Markdown，适合 Web App / 聊天回复
  display_json    — 中文键名的 JSON 字符串（可选给前端表格组件）
  valid           — 是否成功生成展示内容
  error           — 失败原因

说明：
  - 标签映射与 examples/labels-zh.json 保持一致；Dify 云端无法读仓库文件，故内嵌 LABELS。
  - 若上游 valid=false 或未连线 result，本节点 valid=false。
"""

import json

# 与 examples/labels-zh.json 同步
SECTION_LABELS = {
    "basic": "基本信息",
    "education": "教育背景",
    "work_experience": "工作/项目经历",
    "projects": "项目经历",
    "skills": "技能特长",
    "summary": "职业摘要",
}

FIELD_LABELS = {
    "basic": {
        "name": "姓名",
        "phone": "联系电话",
        "email": "电子邮箱",
        "city": "所在城市",
        "years_of_experience": "工作年限（年）",
        "_email_invalid": "邮箱格式异常",
    },
    "education": {
        "school": "学校",
        "major": "专业",
        "degree": "学历",
        "start_date": "入学时间",
        "end_date": "毕业时间",
    },
    "work_experience": {
        "company": "公司/项目",
        "title": "职位",
        "start_date": "开始时间",
        "end_date": "结束时间",
        "description": "职责描述",
    },
    "projects": {
        "name": "项目名称",
        "role": "担任角色",
        "start_date": "开始时间",
        "end_date": "结束时间",
        "description": "项目描述",
        "tech_stack": "技术栈",
    },
}

ARRAY_ITEM_PREFIX = {
    "education": "教育经历",
    "work_experience": "经历",
    "projects": "项目",
}


def _fmt(value):
    """将 null / 空值格式化为展示用占位符。"""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value).strip()
    return s if s else "—"


def _fmt_period(start, end):
    s, e = _fmt(start), _fmt(end)
    if s == "—" and e == "—":
        return "—"
    if e == "—":
        return "{0} 至今".format(s)
    return "{0} ~ {1}".format(s, e)


def _translate_keys(obj, key_map):
    """将 dict 的英文键替换为中文键（浅层或递归一层列表项）。"""
    if not isinstance(obj, dict):
        return obj
    out = {}
    for k, v in obj.items():
        label = key_map.get(k, k)
        if isinstance(v, list):
            out[label] = [
                _translate_keys(item, key_map) if isinstance(item, dict) else item
                for item in v
            ]
        elif isinstance(v, dict):
            out[label] = _translate_keys(v, key_map)
        else:
            out[label] = v
    return out


def to_display_json(data):
    """生成中文键名的 JSON 对象。"""
    if not isinstance(data, dict):
        return {}
    out = {}
    if "basic" in data and isinstance(data["basic"], dict):
        out[SECTION_LABELS["basic"]] = _translate_keys(
            data["basic"], FIELD_LABELS["basic"]
        )
    for section in ("education", "work_experience", "projects"):
        items = data.get(section)
        if not isinstance(items, list) or not items:
            continue
        sec_label = SECTION_LABELS[section]
        key_map = FIELD_LABELS.get(section, {})
        out[sec_label] = [_translate_keys(item, key_map) for item in items]
    skills = data.get("skills")
    if isinstance(skills, list) and skills:
        out[SECTION_LABELS["skills"]] = skills
    if data.get("summary"):
        out[SECTION_LABELS["summary"]] = data["summary"]
    return out


def to_display_markdown(data):
    """生成面向最终用户的中文 Markdown 文本。"""
    if not isinstance(data, dict):
        return ""

    lines = []

    basic = data.get("basic") or {}
    if isinstance(basic, dict):
        lines.append("## {0}".format(SECTION_LABELS["basic"]))
        rows = []
        for key in ("name", "phone", "email", "city", "years_of_experience"):
            if key not in FIELD_LABELS["basic"]:
                continue
            val = basic.get(key)
            if val is None and key != "name":
                continue
            rows.append("| {0} | {1} |".format(FIELD_LABELS["basic"][key], _fmt(val)))
        if basic.get("_email_invalid"):
            rows.append("| {0} | 是 |".format(FIELD_LABELS["basic"]["_email_invalid"]))
        if rows:
            lines.append("| 字段 | 内容 |")
            lines.append("| --- | --- |")
            lines.extend(rows)
        lines.append("")

    edu_list = data.get("education") or []
    if isinstance(edu_list, list) and edu_list:
        lines.append("## {0}".format(SECTION_LABELS["education"]))
        for i, item in enumerate(edu_list, 1):
            if not isinstance(item, dict):
                continue
            prefix = ARRAY_ITEM_PREFIX["education"]
            title_parts = [item.get("school"), item.get("major"), item.get("degree")]
            title = " · ".join([_fmt(p) for p in title_parts if p not in (None, "")])
            lines.append("### {0} {1}".format(prefix, i))
            lines.append("- **{0}**：{1}".format(
                FIELD_LABELS["education"]["school"], _fmt(item.get("school"))
            ))
            if item.get("major"):
                lines.append("- **{0}**：{1}".format(
                    FIELD_LABELS["education"]["major"], _fmt(item.get("major"))
                ))
            if item.get("degree"):
                lines.append("- **{0}**：{1}".format(
                    FIELD_LABELS["education"]["degree"], _fmt(item.get("degree"))
                ))
            period = _fmt_period(item.get("start_date"), item.get("end_date"))
            if period != "—":
                lines.append("- **时间**：{0}".format(period))
        lines.append("")

    work_list = data.get("work_experience") or []
    if isinstance(work_list, list) and work_list:
        lines.append("## {0}".format(SECTION_LABELS["work_experience"]))
        for i, item in enumerate(work_list, 1):
            if not isinstance(item, dict):
                continue
            company = _fmt(item.get("company"))
            title = item.get("title")
            heading = company
            if title:
                heading = "{0}（{1}）".format(company, _fmt(title))
            lines.append("### {0} {1}".format(ARRAY_ITEM_PREFIX["work_experience"], i))
            lines.append("- **{0}**：{1}".format(
                FIELD_LABELS["work_experience"]["company"], company
            ))
            if title:
                lines.append("- **{0}**：{1}".format(
                    FIELD_LABELS["work_experience"]["title"], _fmt(title)
                ))
            period = _fmt_period(item.get("start_date"), item.get("end_date"))
            if period != "—":
                lines.append("- **时间**：{0}".format(period))
            desc = item.get("description")
            if desc:
                lines.append("- **{0}**：{1}".format(
                    FIELD_LABELS["work_experience"]["description"], _fmt(desc)
                ))
        lines.append("")

    proj_list = data.get("projects") or []
    if isinstance(proj_list, list) and proj_list:
        lines.append("## {0}".format(SECTION_LABELS["projects"]))
        key_map = FIELD_LABELS["projects"]
        for i, item in enumerate(proj_list, 1):
            if not isinstance(item, dict):
                continue
            lines.append("### {0} {1}".format(ARRAY_ITEM_PREFIX["projects"], i))
            for key in key_map:
                val = item.get(key)
                if val is None or val == "":
                    continue
                if key in ("start_date", "end_date"):
                    continue
                if key == "tech_stack" and isinstance(val, list):
                    val = "、".join(str(x) for x in val)
                lines.append("- **{0}**：{1}".format(key_map[key], _fmt(val)))
            period = _fmt_period(item.get("start_date"), item.get("end_date"))
            if period != "—":
                lines.append("- **时间**：{0}".format(period))
        lines.append("")

    skills = data.get("skills") or []
    if isinstance(skills, list) and skills:
        lines.append("## {0}".format(SECTION_LABELS["skills"]))
        lines.append("、".join(str(s) for s in skills if s))
        lines.append("")

    summary = data.get("summary")
    if summary:
        lines.append("## {0}".format(SECTION_LABELS["summary"]))
        lines.append(_fmt(summary))
        lines.append("")

    return "\n".join(lines).strip()


def _parse_result(result):
    """解析上游 result 字符串或 dict。"""
    if result is None or result == "":
        return None, "未收到 result（请绑定上一代码节点的 result 输出）"
    if isinstance(result, dict):
        return result, None
    if isinstance(result, str):
        try:
            data = json.loads(result)
        except json.JSONDecodeError as e:
            return None, "result 不是合法 JSON: {0}".format(e)
        if not isinstance(data, dict):
            return None, "result 根节点必须为 object"
        return data, None
    return None, "不支持的 result 类型: {0}".format(type(result).__name__)


def main(result=None, **kwargs):
    """
    Dify 入口。推荐仅配置输入变量 result，绑定 code-node-resume 的 result。
    """
    data, err = _parse_result(result)
    if err:
        return {
            "valid": False,
            "result": result if isinstance(result, str) else "",
            "display_markdown": "",
            "display_json": "",
            "error": err,
        }

    display_obj = to_display_json(data)
    markdown = to_display_markdown(data)
    result_str = json.dumps(data, ensure_ascii=False) if isinstance(result, dict) else (result or json.dumps(data, ensure_ascii=False))

    return {
        "valid": True,
        "result": result_str,
        "display_markdown": markdown,
        "display_json": json.dumps(display_obj, ensure_ascii=False),
        "error": "",
    }
