#!/usr/bin/env python3
"""生成当日 BEC 学习内容（调用 DeepSeek API）。"""

import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent.parent

WEEKS = [
    ("第1周 摸底与基础", "商务英语基础词汇、复习常用时态与句式、建立每日学习习惯"),
    ("第2周 招聘与职位", "职位描述、招聘流程、简历关键词、人才市场词汇"),
    ("第3周 面试（上）", "面试提问、候选人评估、自我介绍、常见面试句型"),
    ("第4周 面试（下）", "深度追问、情景问题、录用/拒绝沟通、薪资谈判词汇"),
    ("第5周 邮件写作", "邮件结构、确认/跟进/催办/致歉句型、语气与礼貌度"),
    ("第6周 电话沟通", "电话约谈、信息确认、听不清时的应对、会议预约"),
    ("第7周 薪酬与福利", "薪酬结构、福利政策、五险一金相关表达、offer 沟通"),
    ("第8周 员工关系", "入职/离职/转岗、员工关怀、投诉与冲突处理"),
    ("第9周 绩效与培训", "绩效评估、反馈表达、培训安排、晋升话题"),
    ("第10周 商务综合", "图表描述、公司介绍、数据汇报、跨文化沟通"),
    ("第11周 真题冲刺", "BEC Vantage 真题题型、时间管理、弱项补强"),
    ("第12周 考前回顾", "高频词汇复盘、写作模板、口语模拟、应试策略"),
]


def load_config() -> dict:
    with open(BASE / "config.json", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(cfg: dict, day: int, week_title: str, week_focus: str) -> str:
    return f"""你是一位经验丰富的 BEC {cfg['level']} 老师，为一位 HR 学习者设计今日学习内容。

今天是学习第 {day} 天，本周主题：{week_title}（{week_focus}）。
该学习者每天约投入 {cfg['study_minutes_per_day']} 分钟，目标是通过 BEC {cfg['level']} 并在 HR 工作中流利使用英文（英文邮件、候选人电话/面试、阅读英文简历）。
该学习者的弱项和重点：{'、'.join(cfg.get('focus_areas', []))}。口语任务要给出示范表达、跟读/复述建议；写作任务要给出模板化结构。

请按以下 markdown 结构输出当天内容（语言：讲解用中文，示例/练习用英文）：

## 今日主题
一句话说明今天学什么、为什么重要。

## 核心词汇（8-10 个）
每个词一行：**单词** 音标 / 词性 / 中文释义 / HR 场景例句（英文）。

## 每日阅读短文（约 250 词）
一篇贴合本周主题的商务英文短文，难度适合 BEC {cfg['level']}，附 3-4 个英文理解题，并额外给出 4-6 个文中生词/短语的中文注释（帮助扫清阅读障碍）。

## 听力 / 口语任务
一个结合 HR 场景的口语话题，附 2-3 个提示问题和表达要点。

## 写作任务
一道 BEC 风格写作题（邮件或便条），附 2-3 条答题要点。

## 参考答案与讲解
给出阅读题答案、口语示范要点、写作示范（约 80 词）及易错点讲解。

总长度控制在 1200 词以内，内容要具体、可直接上手练。"""


def build_quiz_prompt(cfg: dict, week_no: int, week_title: str, week_focus: str) -> str:
    return f"""你是一位经验丰富的 BEC {cfg['level']} 老师，今天需要为学习者出「本周周测」。

本周是第 {week_no} 周，主题：{week_title}（{week_focus}）。
该学习者目标是通过 BEC {cfg['level']} 并在 HR 工作中流利使用英文（英文邮件、候选人电话/面试、阅读英文简历）。

请按以下 markdown 结构输出本周小测（语言：题目与短文用英文，讲解与解析用中文）：

## 本周回顾
用 3-5 句中文总结本周学习主题和核心知识点。

## 词汇小测（10 题）
10 道选择题，覆盖本周商务词汇和固定搭配，每题给出 A-D 四个选项。

## 阅读小测
一篇 200-250 词的商务英文短文（贴合本周主题），附 4 道理解题（英文）。

## 写作小测
一道 BEC 风格写作题（邮件或便条），附答题要点。

## 参考答案与解析
词汇题逐题给出答案和简短解析；阅读题给出答案；写作题给出示范（约 80 词）。

总长度控制在 1400 词以内。"""


def call_deepseek(api_key: str, model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一位专业的商务英语（BEC）备考教练。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
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
    cfg = load_config()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    model = os.environ.get("DEEPSEEK_MODEL", "").strip() or "deepseek-v4-flash"
    if not api_key:
        print("错误：缺少 DEEPSEEK_API_KEY 环境变量", file=sys.stderr)
        return 1

    start = datetime.date.fromisoformat(cfg["start_date"])
    today = datetime.date.today()
    day = max(1, (today - start).days + 1)
    week_idx = min((day - 1) // 7, len(WEEKS) - 1)
    week_title, week_focus = WEEKS[week_idx]

    if today.weekday() == 6:  # 周日：本周周测
        week_no = week_idx + 1
        prompt = build_quiz_prompt(cfg, week_no, week_title, week_focus)
        print(f"第 {week_no} 周周测内容已生成（{week_title}）")
    else:
        prompt = build_prompt(cfg, day, week_title, week_focus)
        print(f"Day {day} 内容已生成（{week_title}）")
    content = call_deepseek(api_key, model, prompt)
    (BASE / "today_content.md").write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
