# BEC 每日学习推送系统（飞书 + GitHub Actions）

每天上午 10:00，系统自动用 AI 生成当天 BEC 学习内容，以卡片形式推送到你的飞书群，卡片上带「今日打卡」按钮。

## 系统是怎么工作的

1. GitHub Actions 每天定时触发（北京时间 10:00）
2. 脚本根据「开始日期 + 12 周学习大纲」算出今天是第几天、属于哪个主题周
3. 调用 DeepSeek API 生成当天内容（核心词汇 + 每日阅读短文 + 听力/口语/写作 + 参考答案）；每周日自动改为推送「本周周测」
4. 以飞书消息卡片推送到你的群，底部带「今日打卡」按钮（点击打开你的飞书打卡表）

## 你需要做的 3 步

### 第 1 步：飞书建机器人，拿到 Webhook

1. 飞书里建一个群（可以只拉自己，或拉一个「仅自己」的群）
2. 群设置 → 群机器人 → 添加机器人 → 自定义机器人
3. 复制机器人的 Webhook 地址（形如 `https://open.feishu.cn/open-apis/bot/v2/hook/xxx`）

### 第 2 步：GitHub 建仓库并填密钥

1. 在 GitHub 新建一个仓库（例如 `bec-feishu`，私有/公开都可以）
2. 把本目录下所有文件推送到仓库
3. 仓库 Settings → Secrets and variables → Actions → New repository secret，添加：
   - `FEISHU_WEBHOOK_URL`：第 1 步复制的 Webhook 地址
   - `DEEPSEEK_API_KEY`：DeepSeek 的 API Key（用于每天生成内容）
   - `DEEPSEEK_MODEL`（可选）：默认 `deepseek-chat`

### 第 3 步：准备打卡表（可选但推荐）

1. 在飞书「多维表格」新建一张表，列：日期 / 完成情况
2. 打卡表链接已填在 `config.json` 的 `checkin_url`（也可改用 GitHub 的 `CHECKIN_URL` 密钥覆盖）
3. 以后每天点击卡片上的「今日打卡」按钮就会打开这张表，勾选完成

## 手动测试

仓库 Actions 页面 → 选择 `Daily BEC Push` → Run workflow，即可立即推送一次，不用等明天 10 点。

## 常用调整

- **改推送时间**：编辑 `.github/workflows/daily-bec.yml` 里的 `cron`（`0 2 * * *` = 北京时间 10:00，UTC+8）
- **改学习级别 / 开始日期**：编辑 `config.json`
- **换 AI 模型**：在 GitHub secret 里加 `DEEPSEEK_MODEL`（如 `deepseek-reasoner`）

## 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/generate_content.py` | 生成当天学习内容 |
| `scripts/push_feishu.py` | 组装飞书卡片并推送 |
| `.github/workflows/daily-bec.yml` | 每日定时任务 |
| `config.json` | 级别、开始日期等配置 |
| `syllabus.md` | 12 周学习大纲 |
