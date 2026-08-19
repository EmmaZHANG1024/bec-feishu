#!/usr/bin/env python3
"""生成当日 BEC 学习内容（调用 DeepSeek API）。
当日卡片不含参考答案；参考答案写入飞书答题表，次日随批改卡片推送。
"""

import datetime
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent.parent

WEEKS = [
    ("第1周 摸底与招聘入门", "摸底测试、基础复习、职位描述与简历关键词（HR 专项）"),
    ("第2周 面试沟通", "面试提问、候选人评估、情景问题、录用沟通（HR 专项）"),
    ("第3周 薪酬福利与Offer", "薪酬结构、福利政策、薪资谈判、Offer 沟通（HR 专项）"),
    ("第4周 员工关系与绩效", "入职离职转岗、员工关怀、绩效评估、培训发展（HR 专项）"),
    ("第5周 市场营销", "产品、推广、广告、市场报告（全行业话题）"),
    ("第6周 财务", "预算、现金流、成本、财务报表基础词汇（全行业话题）"),
    ("第7周 销售与客户服务", "销售话术、客户沟通、投诉处理（全行业话题）"),
    ("第8周 生产运营与物流", "供应链、库存、交付、质量控制（全行业话题）"),
    ("第9周 公司战略与发展", "企业介绍、并购、增长、跨文化商务（全行业话题）"),
    ("第10周 阅读写作真题专练", "BEC 阅读 5 种题型、写作 Part 1/Part 2 专练"),
    ("第11周 听力口语真题专练", "BEC 听力 3 部分、口语 3 部分专练"),
    ("第12周 全真模考与考前回顾", "计时模考、错题复盘、高频词汇冲刺"),
]

ANSWER_MARKER = "## 参考答案与讲解"
FIELD_DATE = "日期"
FIELD_ANSWERS = "参考答案"


def load_config() -> dict:
    with open(BASE / "config.json", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(cfg: dict, day: int, week_title: str, week_focus: str) -> str:
    return f"""你是一位经验丰富的 BEC {cfg['level']} 老师，为一位 HR 学习者设计今日学习内容。

今天是学习第 {day} 天，本周主题：{week_title}（{week_focus}）。
该学习者每天约投入 {cfg['study_minutes_per_day']} 分钟，目标是通过 BEC {cfg['level']} 并在 HR 工作中流利使用英文（英文邮件、候选人电话/面试、阅读英文简历）。
该学习者的重点：{'、'.join(cfg.get('focus_areas', []))}。每日需要批改的练习是阅读、听力、写作、口语（口语以文字稿形式批改），请务必在最后的「参考答案与讲解」中给出前三项的答案与讲解；口语给示范要点即可。

请按以下 markdown 结构输出当天内容（语言：讲解用中文，题目与材料用英文）：

## 今日主题
一句话说明今天学什么、为什么重要。

## 核心词汇（8-10 个）
每个词一行：**单词** 音标 / 词性 / 中文释义 / HR 场景例句（英文）。

## 每日阅读短文（约 250 词）
一篇贴合本周主题的商务英文短文，难度适合 BEC {cfg['level']}，附 3-4 个英文理解题。

## 听力任务
一段约 150 词的英文商务对话（以文字材料呈现，先让学习者听/读一遍再作答），附 3-4 个英文理解题。提示学习者：可配合剑桥官网 B2 Business Vantage 免费样题音频做真实听力练习。

## 口语任务（录音并写出口语稿，次日批改）
一个结合本周主题的口语话题，附 2-3 个提示问题；提示学习者先自己说并录音，再把口语稿写入答题表供次日批改。

## 写作任务
一道 BEC 风格写作题（邮件或便条），附 2-3 条答题要点。

## 参考答案与讲解
给出阅读、听力、写作的参考答案与简要讲解（口语可给示范要点，但重点是前三项）。

注意：除「参考答案与讲解」这一节外，前面的题目部分绝对不要出现任何答案。总长度控制在 1200 词以内。"""


def build_exam_prompt(cfg: dict, day: int, week_title: str, week_focus: str) -> str:
    return f"""你是一位经验丰富的 BEC {cfg['level']} 老师，为学习者出「真题题型专练」内容。

今天是学习第 {day} 天，本周主题：{week_title}（{week_focus}）。
该学习者目标是高分通过 BEC {cfg['level']}，需要熟悉真题题型并控制答题时间（每天约 60 分钟）。

请按以下 markdown 结构输出（题目用英文，提示与讲解用中文）：

## 今日专练说明
3-5 句中文说明今天重点练什么题型、答题时间建议。

## 阅读专练
按 BEC 阅读真题题型出题（匹配题 / 多项选择 / 句子填空 / 完形填空 / 改错题轮流安排），给出 1 组题（含原文材料与题干）。

## 听力专练
一段约 180 词的英文商务对话或独白（文字版，提示配合官方样题音频练习），按听力真题题型出 3-4 题（填空/选择/匹配轮换）。

## 写作专练
按 BEC 写作真题出题：Part 1（40-50 词内部短函）或 Part 2（120-140 词报告/提议/邮件），交替安排，写明词数要求和答题要点。

## 口语专练
按 BEC 口语真题题型出题（Part 2 个人陈述或 Part 3 双人讨论），给出任务说明、提示问题和示范要点。

## 参考答案与讲解
给出阅读、听力、写作的参考答案与讲解（写作给出标注词数的示范），口语给出示范要点。

注意：除「参考答案与讲解」这一节外，前面的题目部分绝对不要出现任何答案。"""


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


def build_answers_prompt(tasks: str) -> str:
    return f"""以下是今天已经生成的学习任务。请只输出「## 参考答案与讲解」这一节（标题必须保持为「## 参考答案与讲解」），内容包括阅读、听力、写作的参考答案与讲解，口语给出示范要点。不要重复题目原文。

### 今日任务
{tasks[:3000]}"""


def call_deepseek(api_key: str, model: str, prompt: str, max_tokens: int = 4000) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一位专业的商务英语（BEC）备考教练。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
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


def store_answers(app_token: str, table_id: str, date_str: str, answers: str) -> None:
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if not (app_id and app_secret):
        raise RuntimeError("缺少飞书应用配置")
    token = get_tenant_token(app_id, app_secret)
    result = feishu(
        "GET",
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size=100",
        token,
    )
    for item in result.get("data", {}).get("items", []):
        if str(item.get("fields", {}).get(FIELD_DATE, "") or "").startswith(date_str):
            feishu(
                "PUT",
                f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{item['record_id']}",
                token,
                {"fields": {FIELD_ANSWERS: answers}},
            )
            return
    feishu(
        "POST",
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
        token,
        {"fields": {FIELD_DATE: date_str, FIELD_ANSWERS: answers}},
    )


def split_tasks_and_answers(content: str) -> tuple:
    match = re.search(r"^#{2,3}\s*参考答案", content, flags=re.MULTILINE)
    idx = match.start() if match else content.find(ANSWER_MARKER)
    if idx == -1:
        return content.strip(), ""
    return content[:idx].strip(), content[idx:].strip()


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

    if today.weekday() == 6:  # 周日：本周周测（答案随卡片一起给）
        week_no = week_idx + 1
        prompt = build_quiz_prompt(cfg, week_no, week_title, week_focus)
        content = call_deepseek(api_key, model, prompt, max_tokens=3000)
        (BASE / "today_content.md").write_text(content, encoding="utf-8")
        print(f"第 {week_no} 周周测内容已生成（{week_title}）")
        return 0

    if week_idx >= 9:  # 第 10-12 周：真题题型专练
        prompt = build_exam_prompt(cfg, day, week_title, week_focus)
    else:
        prompt = build_prompt(cfg, day, week_title, week_focus)
    content = call_deepseek(api_key, model, prompt, max_tokens=4000)
    tasks, answers = split_tasks_and_answers(content)
    if not answers:
        print("参考答案未生成，自动重试一次", file=sys.stderr)
        content = call_deepseek(api_key, model, prompt, max_tokens=4000)
        tasks, answers = split_tasks_and_answers(content)
    if not answers:
        print("改用答案专项生成", file=sys.stderr)
        answers = call_deepseek(api_key, model, build_answers_prompt(tasks), max_tokens=2500)
        if not answers.startswith("#"):
            answers = "## 参考答案与讲解\n\n" + answers
    (BASE / "today_content.md").write_text(tasks, encoding="utf-8")
    print(f"Day {day} 任务内容已生成（{week_title}，不含答案）")

    app_token = os.environ.get("BITABLE_APP_TOKEN", "").strip()
    table_id = os.environ.get("BITABLE_TABLE_ID", "").strip()
    if answers and app_token and table_id:
        try:
            store_answers(app_token, table_id, today.isoformat(), answers)
            print("参考答案已存入答题表，次日随批改推送")
        except Exception as exc:  # noqa: BLE001
            print(f"参考答案存入答题表失败：{exc}", file=sys.stderr)
    elif not answers:
        print("警告：本次生成未包含参考答案", file=sys.stderr)
    else:
        print("警告：缺少答题表配置，参考答案未存储", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
