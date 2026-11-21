# 评估指标体系构建工具

从政策文本、文件和网页中挖掘评估维度与候选指标，通过人工审核形成可管理的指标体系。

发布单位：NGAI-LLMSafeContent。发布分支：`release/1.0`；更新日期：2026-11-21；自研代码许可：Apache-2.0，第三方保留原许可。

## 功能

- 多智能体文档检索、维度抽取与指标生成
- 指标审核、增删改查、批量导入、案例管理及关联图谱
- React前端、FastAPI后端、SQLite与Chroma持久化；支持standalone和integration模式

## 安装与快速开始

Python 3.11、Node.js ≥18、npm；模型挖掘另需兼容的Ollama、OpenAI或DeepSeek服务。

从公开仓下载同一发布分支：

```bash
git clone --branch release/1.0 https://github.com/NGAI-LLMSafeContent-OpenSource/Project_1_Construction_of_Evaluation_System-release.git
cd Project_1_Construction_of_Evaluation_System-release
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell改用 .venv\Scripts\Activate.ps1
```

以下命令均以仓库根目录为起点，注释中的外部条件需先准备：

```bash
python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# 编辑 backend/.env，设置自己的数据库目录、Chroma目录和模型服务
(cd frontend && npm ci && npm run build)
(cd backend && python main.py)
# 另一个终端
(cd frontend && npm run dev -- --host 127.0.0.1)
```

## 使用与输出

打开前端页面（通常为5173端口），上传资料或粘贴政策文本，选择挖掘层级并启动任务。审阅候选指标后采纳或修改，通过指标树、案例库和图谱查看结果。后端默认8000端口，可用 `/health` 检查。

## 配置与外部依赖

首次启动使用新建的可写数据库和向量库。模型凭据通过本地.env提供；嵌入模型、外部网页抓取与真实挖掘结果需使用者另行准备和核验。

真实凭据只在自己的运行环境或平台Secrets中配置，不提交.env、用户上传、模型权重或运行结果。原仓文件中的内网服务地址经发布负责人确认按原样保留，使用者应在本地配置自己的可达服务。

## 验证与已知问题

完成对应依赖准备后运行：

```bash
python tools/release_check.py
```

检查包含发布文件完整性、原仓文件一致性与声明的最小测试。它不会自动下载模型或申请API，也不代表全部真实业务/准确率验收。保留的原仓错误、未运行项及外部依赖见 [KNOWN_ISSUES.md](KNOWN_ISSUES.md)。

## 发布版本与文件清单

本版本以原开发仓主分支提交 `fef7c8b5cac5fbeb48bd7d5874ba59c04a3b4942` 为源。功能实现与对应原文件保持一致；README、许可说明和发布辅助材料单独登记。当前功能的必要源码、配置、界面与运行资源保留，明确弃用的原型、历史结果和开发缓存不捆绑。

- [逐文件发布清单](RELEASE_FILES.md)
- [原仓文件与Git对象对应关系](SOURCE_ALIGNMENT.json)
- [完整文件SHA-256及权限](RELEASE_MANIFEST.json)，校验表为SHA256SUMS

校验值按Git存储字节生成；若原.gitattributes规定检出换行转换，请用Git对象或发布检查脚本校验，避免将LF/CRLF误认为源码变化。各公开平台release/1.0使用同一个提交，平台生成的运行分支不属于此发布清单。

## 反馈、贡献与许可证

请通过 [公开仓Issues](https://github.com/NGAI-LLMSafeContent-OpenSource/Project_1_Construction_of_Evaluation_System-release/issues) 提交复现步骤、环境和日志摘要，勿附真实凭据或用户数据。代码问题由课题维护者在原开发仓处理，发布负责人同步审核后的版本；不要仅修一个平台造成分歧。

自研代码采用[Apache-2.0](LICENSE)。模型、数据集、外部服务和第三方代码遵循各自许可与使用条件，见[第三方说明](THIRD_PARTY_NOTICES.md)。
