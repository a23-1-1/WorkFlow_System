"""
Dify 云端 Python3 代码节点 — JD JSON 解析与规范化

输入变量：
  llm_raw_output  绑定 LLM 的结构化输出（object）或 text（string）

输出变量：
  valid   bool
  result  string（JSON 字符串）
  error   string
"""

import json
import re

_WRAPPER_KEYS = ("llm_raw_output", "llm_output", "output", "data", "result", "text")


def _strip_markdown_fence(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _to_obj(raw_value):
    if isinstance(raw_value, dict):
        obj = raw_value
    elif isinstance(raw_value, str):
        cleaned = _strip_markdown_fence(raw_value)
        if not cleaned:
            return None, "LLM 输出为空"
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            return None, "JSON 解析失败: %s" % str(exc)
    else:
        return None, "输入类型不支持: %s" % type(raw_value).__name__

    if not isinstance(obj, dict):
        return None, "根节点必须是 JSON 对象"

    # 兼容偶发包裹层
    if len(obj) == 1:
        key = list(obj.keys())[0]
        if key in _WRAPPER_KEYS and isinstance(obj[key], dict):
            obj = obj[key]

    return obj, ""


def _normalize_jd(data):
    data.setdefault("job_title", None)
    data.setdefault("job_type", None)
    data.setdefault("seniority", None)
    data.setdefault("required_experience", None)
    data.setdefault("education_requirement", None)
    data.setdefault("required_skills", [])
    data.setdefault("preferred_skills", [])
    data.setdefault("responsibilities", [])
    data.setdefault("keywords", [])

    for field in ("required_skills", "preferred_skills", "responsibilities", "keywords"):
        if not isinstance(data.get(field), list):
            data[field] = []
        normalized = []
        seen = set()
        for item in data[field]:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
        data[field] = normalized

    for field in ("job_title", "job_type", "seniority", "required_experience", "education_requirement"):
        value = data.get(field)
        if value is None:
            continue
        text = str(value).strip()
        data[field] = text if text else None

    return data


def main(llm_raw_output=None, **kwargs):
    if llm_raw_output is None:
        for fallback_key in ("text", "llm_output", "output", "data", "result"):
            if fallback_key in kwargs:
                llm_raw_output = kwargs[fallback_key]
                break

    data, err = _to_obj(llm_raw_output)
    if err:
        return {"valid": False, "result": "", "error": err}

    normalized = _normalize_jd(data)

    return {
        "valid": True,
        "result": json.dumps(normalized, ensure_ascii=False),
        "error": ""
    }
