#!/usr/bin/env python3
"""读取飞书多维表格中的昨日答题，调用 DeepSeek 批改，并把反馈写进当天卡片。"""

import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent.parent

FIELD_DATE = "日期"
FIELD_SPEAK = "口语回答"
FIELD_WRITE = "写作回答"
FIELD_STATUS = "批改状态"
FIELD_FEEDBACK = "批改反馈"


def get_tenant_token(app_id: str, app_secret: str) -> str:
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("code") != 0:
        raise RuntimeError(f"获取飞书凭证失败: {data}")
    return data["tenant_access_token"]


def feishu(method: str, url: str, token: str, body=None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
    except urllib.error.HTTPError as exc:
        result = json.loads(exc.read() or b"{}")
    if result.get("code") != 0:
        raise RuntimeError(f"飞书 API 错误: {result}")
    return result


def list_records(token: str, app_token: str, table_id: str) -> list:
    result = feishu(
        "GET",
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size=100",
        token,
    )
    return result.get("data", {}).get("items", [])


def update_record(token: str, app_token: str, table_id: str, record_id: str, fields: dict) -> None:
    feishu(
        "PUT",
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
        token,
        {"fields": fields},
    )


def grade_with_deepseek(api_key: str, model: str, speak: str, write: str) -> str:
    prompt = f"""你是一位严格的 BEC Vantage 阅卷老师。请批改学习者昨天的口语和写作练习，用中文输出反馈。

### 口语回答
{speak or "（未填写）"}

### 写作回答
{write or "（未填写）"}

请严格按以下 markdown 结构输出：

## 口语批改
- 评分（1-10）：x/10
- 优点：1-2 句
- 问题与改进建议：2-3 条，给出更地道的英文表达示范

## 写作批改
- 评分（1-10）：x/10
- 问题清单：逐条指出语法/搭配/格式问题
- 示范改写：给出优化后的完整版本

注意：针对 BEC Vantage 评分标准（内容、组织、语言准确性、词汇丰富度），点评要具体、可执行。"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一位专业的商务英语（BEC）阅卷老师。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 1800,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        print(f"DeepSeek API 错误 {exc.code}: {body}", file=sys.stderr)
        raise
    return data["choices"][0]["message"]["content"]


def main() -> int:
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    app_token = os.environ.get("BITABLE_APP_TOKEN", "").strip()
    table_id = os.environ.get("BITABLE_TABLE_ID", "").strip()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    model = os.environ.get("DEEPSEEK_MODEL", "").strip() or "deepseek-v4-flash"
    if not (app_id and app_secret and app_token and table_id and api_key):
        print("缺少飞书或 DeepSeek 配置，跳过批改", file=sys.stderr)
        return 1

    token = get_tenant_token(app_id, app_secret)
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    records = list_records(token, app_token, table_id)

    feedbacks = []
    graded = 0
    for record in records:
        fields = record.get("fields", {})
        date_val = str(fields.get(FIELD_DATE, "") or "")
        if not date_val.startswith(yesterday):
            continue
        if str(fields.get(FIELD_STATUS, "") or "") == "已批改":
            continue
        speak = str(fields.get(FIELD_SPEAK, "") or "").strip()
        write = str(fields.get(FIELD_WRITE, "") or "").strip()
        if not speak and not write:
            continue
        feedback = grade_with_deepseek(api_key, model, speak, write)
        update_record(
            token,
            app_token,
            table_id,
            record["record_id"],
            {FIELD_STATUS: "已批改", FIELD_FEEDBACK: feedback},
        )
        feedbacks.append(feedback)
        graded += 1
        print(f"已批改 {yesterday} 的答题（第 {graded} 份）")

    if feedbacks:
        (BASE / "yesterday_feedback.md").write_text(
            "\n\n---\n\n".join(feedbacks),
            encoding="utf-8",
        )
        print(f"共批改 {graded} 份答案，反馈已写入今日卡片")
    else:
        if (BASE / "yesterday_feedback.md").exists():
            (BASE / "yesterday_feedback.md").unlink()
        print("昨日无待批改的答题")
    return 0


if __name__ == "__main__":
    sys.exit(main())
