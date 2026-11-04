# 评估指标体系构建工具

发布方 NGAI-LLMSafeContent；版本 1.0；日期 2026-11-04；Apache-2.0。
源仓库 NGAI-LLMSafeContent/Project_1_Construction_of_Evaluation_System，固定提交 fef7c8b5cac5fbeb48bd7d5874ba59c04a3b4942。

公开 backend、frontend 以及确认单允许的初始 framework_now.json。没有开发 SQLite、Chroma 索引、缓存、抓取正文或运行日志。

## 前置条件与安装

Python 3.11（命令名 python3.11，应加入 PATH）、pip >=22.3、Node.js >=18、npm；需要联网下载 PyPI/npm 依赖。建议新建 Python venv，从根目录执行：

```sh
python3.11 -m pip install -r backend/requirements.txt
cd frontend
npm ci --ignore-scripts --no-audit
npm run build
```

复制 backend/.env.example 为自己的 backend/.env，配置 DATABASE_URL、CHROMA_PERSIST_DIR 和所选模型服务。首次启动使用全新可写目录；不得复制开发数据库。定时政策抓取默认关闭，使用者自行确认抓取范围和使用权限后才开启。LLM 服务需使用者自备 API 地址、模型与凭据；凭据不提交版本库。

从 backend/ 运行 `python main.py`（默认端口 8000）；从 frontend/ 运行 `npm run dev -- --host 127.0.0.1`（默认端口 5173）。GET /health 验证健康，GET /api/indicators/framework 获取初始指标。

## 自动验证

根目录 `python tools/release_smoke.py`：隔离安装依赖、运行现有配置测试、前端测试和生产构建，使用全新临时数据库/索引启动后端并验证健康、空库查询和初始指标，再启动生产静态页面 HTTP 检查。没有调用外部 LLM、下载嵌入模型或执行网页抓取；指标自动生成、向量嵌入与语义检索仍需真实模型验证。

完整发布文件和校验见 RELEASE_MANIFEST.json、SHA256SUMS，第三方条件见 THIRD_PARTY_NOTICES.md。
