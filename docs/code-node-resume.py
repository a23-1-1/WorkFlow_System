"""
Dify 云端 Python3 代码节点 — 简历 JSON 解析与规范化

用法：将本文件全文复制到 Dify 工作流「代码」节点（语言选 Python 3）。

输入变量名（必须与 main() 参数名完全一致）：
  llm_raw_output — 绑定上一 LLM 节点的结构化 JSON 输出，或 text 输出

输出变量名：valid、result、error

说明：
  - Dify 会把每个「输入变量名」作为 keyword 传给 main()；未在 main() 中声明的参数会触发
    TypeError: main() got an unexpected keyword argument 'arg2'。请删除未使用的 arg2 等变量。
  - 若 LLM 开启结构化输出，绑定 JSON/object 变量；若为纯文本，绑定 text 即可。
"""

import json
import re

# 简单邮箱正则（过滤明显错误，不保证 RFC 5322 完整合规）
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# LLM 偶发多包一层时的常见键名（仅当顶层只有单一键且值为 dict 时解包一次）
_WRAPPER_KEYS = ("llm_raw_output", "llm_output", "output", "data", "result", "text")


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


def _unwrap_single_key_wrapper(data):
    """
    若 LLM 或上游节点多包一层（如 {"llm_raw_output": {"basic": ...}}），解包一次。
    若已是标准简历结构（含 basic 等字段），保持不变。
    """
    if not isinstance(data, dict) or len(data) != 1:
        return data
    key = next(iter(data))
    inner = data[key]
    if key in _WRAPPER_KEYS and isinstance(inner, dict):
        return inner
    return data


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


def _resolve_raw_input(llm_raw_output=None, **kwargs):
    """优先 llm_raw_output；否则尝试 kwargs 中的常见别名（兼容旧配置）。"""
    if llm_raw_output is not None:
        return llm_raw_output
    for key in ("text", "llm_output", "llm_text", "output"):
        if key in kwargs and kwargs[key] is not None:
            return kwargs[key]
    return None


def _parse_to_dict(raw):
    """将 str 或 dict 转为简历 dict；失败时返回 (None, error_msg)。"""
    if isinstance(raw, dict):
        return _unwrap_single_key_wrapper(raw), None

    if isinstance(raw, str):
        text = _strip_markdown_fence(raw)
        if not text:
            return None, "LLM 输出为空，无法解析 JSON"
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return None, "JSON 解析失败: {0}".format(e)
        if not isinstance(data, dict):
            return None, "JSON 根节点必须为 object"
        return _unwrap_single_key_wrapper(data), None

    return None, "不支持的输入类型: {0}，请绑定 LLM 的 text 或结构化 JSON".format(
        type(raw).__name__
    )


def main(llm_raw_output=None, **kwargs) -> dict:
    """
    Dify 入口：输入变量名必须与参数名一致（推荐仅配置 llm_raw_output）。
    **kwargs 用于忽略界面残留的多余变量（如 arg2），避免 TypeError。
    """
    raw = _resolve_raw_input(llm_raw_output, **kwargs)
    if raw is None:
        return {
            "valid": False,
            "result": "",
            "error": "未收到 LLM 输出（请检查输入变量名是否为 llm_raw_output，并绑定 LLM 输出）",
        }

    data, err = _parse_to_dict(raw)
    if err:
        return {"valid": False, "result": "", "error": err}

    # 若 LLM 只返回 {"basic": {...}}，_normalize_resume 会补全 education/work_experience 等顶层字段
    data = _normalize_resume(data)

    return {
        "valid": True,
        "result": json.dumps(data, ensure_ascii=False),
        "error": "",
    }
