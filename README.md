# BEC 每日学习推送系统（飞书 + GitHub Actions）

每天上午 10:00，系统自动用 AI 生成当天 BEC 学习内容，以卡片形式推送到你的飞书群，卡片上带「今日打卡」按钮。

学习大纲共 12 周：**HR 专项 4 周 + 全行业商务话题 5 周 + 真题专练/模考 3 周**，避免只练 HR 内容导致考试主题覆盖不足。

## 系统是怎么工作的

1. GitHub Actions 每天定时触发（北京时间 10:00）
2. 脚本根据「开始日期 + 12 周学习大纲」算出今天是第几天、属于哪个主题周
3. 调用 DeepSeek API 生成当天内容（核心词汇 + 每日阅读短文 + 听力任务 + 口语自练 + 写作任务，**不含参考答案**）；每周日自动改为推送「本周周测」
4. 以飞书消息卡片推送到你的群，底部带「今日打卡」按钮（点击打开你的飞书打卡表）
5. 次日推送时先读取「每日答题」表中你昨天的口语（文字稿）/阅读/听力/写作答案，对照参考答案批改，**先推送「昨日批改 + 参考答案」卡片，再推送今日任务卡片**

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
   - `CHECKIN_URL`：你的飞书打卡表链接（见第 3 步）
   - `DEEPSEEK_MODEL`（可选）：默认 `deepseek-v4-flash`

### 第 3 步：准备打卡表（可选但推荐）

1. 在飞书「多维表格」新建一张表，列：日期 / 完成情况
2. 把打卡表链接填到 GitHub 的 `CHECKIN_URL` 密钥里（卡片「今日打卡」按钮会打开这张表）
3. 以后每天点击卡片上的「今日打卡」按钮就会打开这张表，勾选完成

## 手动测试

仓库 Actions 页面 → 选择 `Daily BEC Push` → Run workflow，即可立即推送一次，不用等明天 10 点。

## 常用调整

- **改推送时间**：编辑 `.github/workflows/daily-bec.yml` 里的 `cron`（`0 2 * * *` = 北京时间 10:00，UTC+8）
- **改学习级别 / 开始日期**：编辑 `config.json`
- **换 AI 模型**：在 GitHub secret 里加 `DEEPSEEK_MODEL`（默认 `deepseek-v4-flash`）

## 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/grade_answers.py` | 读取答题表并批改昨日答案 |
| `scripts/generate_content.py` | 生成当天学习内容 |
| `scripts/push_feishu.py` | 组装飞书卡片并推送 |
| `.github/workflows/daily-bec.yml` | 每日定时任务 |
| `config.json` | 级别、开始日期等配置 |
| `syllabus.md` | 12 周学习大纲 |

## 互动批改（方案 C）使用说明

1. 在飞书开放平台（open.feishu.cn）创建一个「企业自建应用」，添加权限：**多维表格**（bitable:app，查看、评论、编辑和管理多维表格），并发布版本
2. 把应用添加为打卡表（多维表格）的协作者，权限设为「可编辑」
3. 在打卡表里新建一个工作表，命名为「每日答题」，包含列：日期、阅读回答、听力回答、写作回答、参考答案、批改状态、批改反馈
4. 把应用的 App ID、App Secret，以及多维表格的链接发给配置方，由系统自动解析并填入 GitHub 密钥：
   - `FEISHU_APP_ID` / `FEISHU_APP_SECRET`（飞书应用凭证）
   - `BITABLE_APP_TOKEN` / `BITABLE_TABLE_ID`（答题表定位）
5. 每天完成练习后，在「每日答题」表新建一行：日期填当天，把阅读、听力、写作答案粘贴到对应列；第二天 10:00 先收到「昨日批改 + 参考答案」卡片，再收到今日任务卡片（参考答案列由系统自动填写）
