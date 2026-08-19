#!/usr/bin/env python3
"""把当天生成的内容组装成飞书卡片并推送到群。"""

import datetime
import json
import os
import pathlib
import sys
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(BASE / "config.json", encoding="utf-8") as f:
        return json.load(f)


def build_card(cfg: dict, day: int, body: str, checkin_url: str) -> dict:
    level_label = cfg["level"].upper()
    is_sunday = datetime.date.today().weekday() == 6
    if is_sunday:
        week_no = (day - 1) // 7 + 1
        header_title = f"BEC {level_label} 周测 · 第 {week_no} 周"
    else:
        header_title = f"BEC {level_label} 学习 · 第 {day} 天"
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": header_title},
            "template": "blue",
        },
        "elements": [{"tag": "markdown", "content": body[:5000]}],
    }
    if checkin_url:
        card["elements"].append({"tag": "hr"})
        card["elements"].append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "今日打卡 ✅"},
                        "type": "default",
                        "url": checkin_url,
                    }
                ],
            }
        )
    else:
        card["elements"].append({"tag": "hr"})
        card["elements"].append(
            {
                "tag": "markdown",
                "content": "**完成今日任务后请点击打卡按钮**（需先在飞书多维表格建打卡表，并把链接配置到 `CHECKIN_URL`）。",
            }
        )
    card["elements"].append({"tag": "hr"})
    card["elements"].append(
        {
            "tag": "markdown",
            "content": "✍️ **答题与批改**：完成练习后，打开打卡表 → 「每日答题」工作表 → 新建一行，日期填今天，把**口语（文字稿）/阅读/听力/写作**答案填进对应列；次日 10:00 先收到「昨日批改 + 参考答案」卡片，再收到今日任务卡片。\n\n🎧 **听力练习**：建议配合剑桥官网 B2 Business Vantage 免费样题音频练习真实听力。",
        }
    )
    return card


def build_feedback_card(cfg: dict, day: int, body: str) -> dict:
    level_label = cfg["level"].upper()
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"BEC {level_label} 昨日批改 · 第 {day} 天"},
            "template": "orange",
        },
        "elements": [{"tag": "markdown", "content": body[:5000]}],
    }


def send_card(webhook: str, card: dict) -> bool:
    payload = json.dumps({"msg_type": "interactive", "card": card}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
    except Exception as exc:  # noqa: BLE001
        print(f"推送请求失败：{exc}", file=sys.stderr)
        return False
    if result.get("code") != 0:
        print(f"飞书返回错误：{result}", file=sys.stderr)
        return False
    return True


def main() -> int:
    cfg = load_config()
    webhook = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    checkin_url = os.environ.get("CHECKIN_URL", "").strip() or cfg.get("checkin_url", "")
    if not webhook:
        print("错误：缺少 FEISHU_WEBHOOK_URL 环境变量", file=sys.stderr)
        return 1

    start = datetime.date.fromisoformat(cfg["start_date"])
    today = datetime.date.today()
    day = max(1, (today - start).days + 1)
    mode = sys.argv[1] if len(sys.argv) > 1 else "today"

    if mode == "feedback":
        feedback_file = BASE / "yesterday_feedback.md"
        if not feedback_file.exists():
            print("无昨日批改，跳过反馈卡片")
            return 0
        body = feedback_file.read_text(encoding="utf-8")
        yesterday_day = max(1, ((today - datetime.timedelta(days=1)) - start).days + 1)
        card = build_feedback_card(cfg, yesterday_day, body)
    else:
        content_file = BASE / "today_content.md"
        if content_file.exists():
            body = content_file.read_text(encoding="utf-8")
        else:
            body = "**今日内容生成失败**，请检查 GitHub Actions 日志或 DeepSeek 配置。"
        card = build_card(cfg, day, body, checkin_url)

    if send_card(webhook, card):
        print("卡片已推送到飞书")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
