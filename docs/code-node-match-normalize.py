"""
Dify 云端 Python3 代码节点 — 匹配结果归一化

输入变量：
  llm_raw_output  绑定匹配评分 LLM 输出（object 或 text）

输出变量：
  valid   bool
  result  string（JSON 字符串）
  error   string
"""

import json
import re

_ALLOWED_RECOMMENDATION = ("strong_recommend", "recommend", "hold", "reject")


def _strip_markdown_fence(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_input(raw_value):
    if isinstance(raw_value, dict):
        return raw_value, ""
    if isinstance(raw_value, str):
        cleaned = _strip_markdown_fence(raw_value)
        if not cleaned:
            return None, "LLM 输出为空"
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            return None, "JSON 解析失败: %s" % str(exc)
        if isinstance(obj, dict):
            return obj, ""
        return None, "根节点必须是 JSON 对象"
    return None, "输入类型不支持: %s" % type(raw_value).__name__


def _score_to_int(value):
    if value is None:
        return 0
    try:
        number = int(float(value))
    except Exception:
        return 0
    if number < 0:
        return 0
    if number > 100:
        return 100
    return number


def _normalize_list(items):
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _infer_recommendation(score):
    if score >= 85:
        return "strong_recommend"
    if score >= 70:
        return "recommend"
    if score >= 50:
        return "hold"
    return "reject"


def main(llm_raw_output=None, **kwargs):
    if llm_raw_output is None:
        for fallback_key in ("text", "llm_output", "output", "data", "result"):
            if fallback_key in kwargs:
                llm_raw_output = kwargs[fallback_key]
                break

    data, err = _parse_input(llm_raw_output)
    if err:
        return {"valid": False, "result": "", "error": err}

    score = _score_to_int(data.get("match_score"))
    recommendation = data.get("recommendation")
    if recommendation not in _ALLOWED_RECOMMENDATION:
        recommendation = _infer_recommendation(score)

    normalized = {
        "candidate_name": data.get("candidate_name"),
        "job_title": data.get("job_title"),
        "match_score": score,
        "recommendation": recommendation,
        "matched_points": _normalize_list(data.get("matched_points")),
        "missing_points": _normalize_list(data.get("missing_points")),
        "risk_points": _normalize_list(data.get("risk_points")),
        "interview_focus": _normalize_list(data.get("interview_focus")),
        "reason_summary": data.get("reason_summary")
    }

    if "error" in data:
        normalized["error"] = data.get("error")

    return {
        "valid": True,
        "result": json.dumps(normalized, ensure_ascii=False),
        "error": ""
    }
