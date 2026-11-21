# 发布文件清单

原仓：`NGAI-LLMSafeContent/Project_1_Construction_of_Evaluation_System`；源提交：`fef7c8b5cac5fbeb48bd7d5874ba59c04a3b4942`；分支：`release/1.0`。

本清单逐文件列出发布内容。原有非README实现/配置/资源保持Git对象字节和模式一致；README与发布新增材料单独登记。RELEASE_MANIFEST.json和SHA256SUMS由发布器生成，不形成自引用哈希。

## 来自原仓、原样保留的文件

- `.gitignore`
- `backend/.env.example`
- `backend/agents/__init__.py`
- `backend/agents/dimension_extractor.py`
- `backend/agents/indicator_generator.py`
- `backend/agents/orchestrator.py`
- `backend/agents/policy_retriever.py`
- `backend/api/routes_agents.py`
- `backend/api/routes_cases.py`
- `backend/api/routes_indicators.py`
- `backend/api/routes_policy_documents.py`
- `backend/main.py`
- `backend/models/schemas.py`
- `backend/modules/evolution_module.py`
- `backend/modules/policy_document_service.py`
- `backend/modules/review_module.py`
- `backend/ontology/__init__.py`
- `backend/ontology/new_indicator_taxonomy.py`
- `backend/requirements.txt`
- `backend/runtime_config.py`
- `backend/scripts/fix_scientific_truthfulness_level.py`
- `backend/scripts/reset_to_new_taxonomy.py`
- `backend/scripts/sync_indicator_taxonomy.py`
- `backend/tests/test_runtime_config.py`
- `backend/utils/llm_client.py`
- `backend/utils/vector_store.py`
- `framework_now.json`
- `frontend/index.html`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/src/App.jsx`
- `frontend/src/components/AgentDashboard.jsx`
- `frontend/src/components/CaseLibrary.jsx`
- `frontend/src/components/EvalDataDemo.jsx`
- `frontend/src/components/IndicatorDetail.jsx`
- `frontend/src/components/IndicatorTree.jsx`
- `frontend/src/components/RelationGraph.jsx`
- `frontend/src/components/ReviewPanel.jsx`
- `frontend/src/config/runtime.js`
- `frontend/src/config/runtime.test.js`
- `frontend/src/main.jsx`
- `frontend/src/services/api.js`
- `frontend/src/styles/index.css`
- `frontend/vite.config.js`

## README及发布新增材料

- `KNOWN_ISSUES.md`
- `LICENSE`
- `README.md`
- `RELEASE_FILES.md`
- `SOURCE_ALIGNMENT.json`
- `THIRD_PARTY_NOTICES.md`
- `release_checks.json`
- `tools/release_check.py`

## 生成的校验文件

- `RELEASE_MANIFEST.json`
- `SHA256SUMS`

## 排除范围

明确弃用的历史原型、旧版本快照、缓存、数据库、用户配置和预跑产物未发布。模型、原始数据/知识库和外部服务按README准备，不以缩减/改写同路径数据文件冒充完整交付。源码原有错误保留，见KNOWN_ISSUES.md。
