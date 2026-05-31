"""
Dify 云端 Python3 代码节点 — 简历 JSON 解析与规范化

用法：将本文件全文复制到 Dify 工作流「代码」节点（语言选 Python 3）。
输入变量名：llm_output（绑定上一 LLM 节点的 text 输出）
输出变量名：valid、result、error
"""

import json
import re

# 简单邮箱正则（过滤明显错误，不保证 RFC 5322 完整合规）
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _strip_markdown_fence(text):
    """去除 LLM 可能返回的 ```json ... ``` 围栏。"""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_email(email):
    """
    简单邮箱校验。
    无效时保留 email 原文，并在 basic 上设置 _email_invalid=True，便于下游条件分支或人工复核。
    若不希望暴露该标记，可改为将 email 置为 null。
    """
    if email is None or email == "":
        return email, False
    if not isinstance(email, str):
        email = str(email)
    email = email.strip()
    if _EMAIL_RE.match(email):
        return email, False
    return email, True


def _normalize_phone(phone):
    """
    手机归一化：去除非数字字符；长度 >= 11 时取末 11 位（常见大陆手机号）。

    局限说明：
    - 假定输入为中国大陆 11 位移动号码或带 +86 / 0086 前缀的写法；
    - 国际号码、座机、带分机（如 010-12345678-123）可能被错误截断；
    - 原文含掩码（如 138****0000）去非数字后位数不足 11，将保留去符号后的数字串。
    """
    if phone is None or phone == "":
        return phone
    if not isinstance(phone, str):
        phone = str(phone)
    raw = phone.strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return raw
    if len(digits) >= 11:
        return digits[-11:]
    return digits


def _dedupe_skills(skills):
    """skills 去重，保留首次出现顺序（大小写不敏感）。"""
    if not isinstance(skills, list):
        return []
    seen = set()
    out = []
    for item in skills:
        if item is None:
            continue
        s = str(item).strip()
        if not s:
            continue
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _normalize_resume(data):
    """顶层与子字段 setdefault，并做邮箱/手机/skills 规范化。"""
    data.setdefault("basic", {})
    data.setdefault("education", [])
    data.setdefault("work_experience", [])
    data.setdefault("skills", [])
    data.setdefault("summary", None)

    if not isinstance(data["basic"], dict):
        data["basic"] = {}
    basic = data["basic"]
    basic.setdefault("name", None)
    basic.setdefault("phone", None)
    basic.setdefault("email", None)
    basic.setdefault("city", None)
    basic.setdefault("years_of_experience", None)

    email, invalid = _validate_email(basic.get("email"))
    basic["email"] = email
    if invalid:
        basic["_email_invalid"] = True
    else:
        basic.pop("_email_invalid", None)

    if basic.get("phone") is not None:
        basic["phone"] = _normalize_phone(basic["phone"])

    data["skills"] = _dedupe_skills(data.get("skills"))

    if not isinstance(data["education"], list):
        data["education"] = []
    if not isinstance(data["work_experience"], list):
        data["work_experience"] = []

    return data


def main(llm_output: str) -> dict:
    text = _strip_markdown_fence(llm_output)

    if not text:
        return {
            "valid": False,
            "result": "",
            "error": "LLM 输出为空，无法解析 JSON",
        }

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "result": "",
            "error": "JSON 解析失败: {0}".format(e),
        }

    if not isinstance(data, dict):
        return {
            "valid": False,
            "result": "",
            "error": "JSON 根节点必须为 object",
        }

    data = _normalize_resume(data)

    return {
        "valid": True,
        "result": json.dumps(data, ensure_ascii=False),
        "error": "",
    }
