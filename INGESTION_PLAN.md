# Dify Flow Ingestion Plan / Dify 流程摄取方案

## Overview | 概述
- **EN:** This guide describes how to build a Dify Flow that ingests documents via the `sys.files` trigger, parses them with Unstructured (hi_res mode), chunks content, extracts structured metadata with an LLM, and writes results to both BM25 and vector indexes. Optional branches handle OCR and image embeddings.
- **中文：** 本指南讲解如何在 Dify Flow 中使用 `sys.files` 作为入口，借助 Unstructured（开启 hi_res）解析文档，完成分块、结构化元数据抽取，并将结果写入 BM25 与向量索引，可选分支负责 OCR 及图片向量入库。

## Prerequisites | 前置条件
- **EN:** Install Docker & Docker Compose; clone the repo and ensure the `docker/docker-compose.v2.yaml` override is present. Copy `docker/.env.example` to `.env` and append retriever/OCR/OpenSearch variables (`RETRIEVER_BASE_URL`, `RETRIEVER_PORT`, `PPOCR_PORT`, `OCR_BASE_URL`, `ALI_EMB_*`, `ALI_RERANK_MODEL`, OpenSearch credentials, `TEXT_EMB_DIM`, `IMAGE_EMB_DIM`).
- **中文：** 已安装 Docker 与 Docker Compose；拉取仓库并确认存在 `docker/docker-compose.v2.yaml` 覆盖文件。复制 `docker/.env.example` 为 `.env`，并追加检索/OCR/OpenSearch 所需变量（如 `RETRIEVER_BASE_URL`、`RETRIEVER_PORT`、`PPOCR_PORT`、`OCR_BASE_URL`、`ALI_EMB_*`、`ALI_RERANK_MODEL`、OpenSearch 凭据、`TEXT_EMB_DIM`、`IMAGE_EMB_DIM`）。

## Bring Up Services | 启动服务
- **EN:** Pre-build the PP-OCRv4 slim image: `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.v2.yaml build ocr`.
- **中文：** 预构建 PP-OCRv4 slim 镜像：`docker compose -f docker/docker-compose.yaml -f docker/docker-compose.v2.yaml build ocr`。
- **EN:** Launch base + ingestion stack: `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.v2.yaml --profile opensearch --profile unstructured up -d api worker web retriever ocr opensearch unstructured`.
- **中文：** 启动基础与摄取服务栈：`docker compose -f docker/docker-compose.yaml -f docker/docker-compose.v2.yaml --profile opensearch --profile unstructured up -d api worker web retriever ocr opensearch unstructured`。
- **EN:** Health checks: `curl http://localhost:7001/healthz` (retriever), `curl http://localhost:8504/healthz` (OCR), `curl -k https://localhost:9200` (OpenSearch, adjust for TLS), `curl http://localhost:8000/health` (Unstructured API).
- **中文：** 健康检查：`curl http://localhost:7001/healthz`（retriever）、`curl http://localhost:8504/healthz`（OCR）、`curl -k https://localhost:9200`（OpenSearch，视 TLS 设置调整）、`curl http://localhost:8000/health`（Unstructured API）。

## Configure Dify Tools | 配置 Dify 工具
- **EN:** Create HTTP Tool `IndexBM25` → `POST /index/bm25` (retriever) with body containing chunk text and metadata (doc/chunk IDs, titles, page, structured fields).
- **中文：** 新建 HTTP 工具 `IndexBM25` 指向 retriever 的 `POST /index/bm25`，请求体含分块文本、元数据（文档/块 ID、标题、页码、结构化字段）。
- **EN:** Create HTTP Tool `UpsertTextVectors` → `POST /upsert/text` (retriever) for batch text embedding writes; include tenant/user identifiers for RBAC.
- **中文：** 新建 HTTP 工具 `UpsertTextVectors` → `POST /upsert/text` 用于批量文本向量写入，并传入租户/用户标识用于权限控制。
- **EN:** Optional HTTP Tool `UpsertImageVectors` → `POST /upsert/image` when you also persist image embeddings/OCR captions.
- **中文：** 可选新增工具 `UpsertImageVectors` → `POST /upsert/image`，同时写入图片向量与 OCR 文本/描述。
- **EN:** If retriever requires authentication, configure `Authorization: Bearer {{ RETRIEVER_API_KEY }}` in each tool.
- **中文：** 若 retriever 需鉴权，请在每个工具中配置 `Authorization: Bearer {{ RETRIEVER_API_KEY }}` 头部。

## Flow Construction | Flow 构建步骤
1. **Start (`sys.files`) / 启动节点（`sys.files`）**
   - EN: Accept uploaded documents; retain owner, tenant ID, filename, MIME type.
   - 中文：接受文件上传，保留上传者、租户 ID、文件名、MIME 类型等信息。
2. **Unstructured Parsing / Unstructured 解析**
   - EN: Call Unstructured with `hi_res=true`; request text, `page_number`, `element_id`, block type, image list.
   - 中文：调用 Unstructured 并开启 `hi_res=true`，获取文本、`page_number`、`element_id`、块类型及图片列表。
3. **Chunking (size=800, overlap=140) / 分块（大小 800，重叠 140）**
   - EN: Enable heading/title propagation so chunks inherit section titles; output `chunk_id`, `doc_id`, page, headings.
   - 中文：开启标题增强，使分块继承章节标题；输出 `chunk_id`、`doc_id`、页码、标题等信息。
4. **Metadata Extraction LLM / 元数据抽取 LLM**
   - EN: Prompt LLM to produce strict JSON with keys: `case_id`, `court`, `trial_level`, `cause_of_action`, `date`, `amount`, `judgement`, `citations`, `disputes`, `tags` (array). Validate JSON and retry/failover if malformed.
   - 中文：提示 LLM 返回严格 JSON，字段包括 `case_id`、`court`、`trial_level`、`cause_of_action`、`date`、`amount`、`judgement`、`citations`、`disputes`、`tags`（数组），并对 JSON 做校验，异常时重试或转失败分支。
5. **Write BM25 Index / 写入 BM25 索引**
   - EN: Map chunk batches and metadata to `IndexBM25`; keep batch size reasonable (≤50 chunks); include RBAC fields (`tenant_id`, `owner_id`, `allowed_user_ids`, etc.).
   - 中文：将分块批处理与元数据映射到 `IndexBM25`，保持单次提交不超过约 50 个分块，并写入权限字段（`tenant_id`、`owner_id`、`allowed_user_ids` 等）。
6. **Write Text Vectors / 写入文本向量**
   - EN: Feed same batches to `UpsertTextVectors` so retriever requests Alibaba text embedding API and stores vectors in OpenSearch.
   - 中文：将同批分块传递给 `UpsertTextVectors`，由 retriever 调用阿里文本向量 API 写入 OpenSearch。
7. **Optional Image Branch / 可选图片分支**
   - EN: For each image, call OCR service (`POST http://ocr:8504/ocr`) and optional caption model; send results to `UpsertImageVectors` with OCR text, confidence, image metadata.
   - 中文：对每个图片调用 OCR 服务（`POST http://ocr:8504/ocr`）及可选描述模型，将 OCR 文本、置信度、图片元数据提交到 `UpsertImageVectors`。
8. **Completion / 完成节点**
   - EN: Return ingestion summary (document ID, chunk count, failed items) for monitoring.
   - 中文：返回摄取摘要（文档 ID、分块数量、失败项）供监控使用。

## OpenSearch Index Blueprint | OpenSearch 索引设计
- **EN:** Create an index (e.g. `legal-documents`) with fields: `text` (text), structured fields (`case_id`, `court`, etc. as keyword/date), `chunk_id` (keyword), `page_number` (integer), `tags` (keyword array), `text_vec` and `image_vec` as `knn_vector` with dimensions from environment variables. Enable `index.knn=true` and tune HNSW parameters (`m=32`, `ef_construction=200`, `ef_search` >= topK).
- **中文：** 创建索引（如 `legal-documents`），字段包括：`text`（text 类型）、结构化字段（`case_id`、`court` 等为 keyword/date）、`chunk_id`（keyword）、`page_number`（integer）、`tags`（keyword 数组）、`text_vec` 与 `image_vec`（`knn_vector`，维度取自环境变量）。启用 `index.knn=true` 并调优 HNSW 参数（如 `m=32`、`ef_construction=200`、`ef_search` ≥ topK）。

## Validation & Monitoring | 验证与监控
- **EN:** Ingest sample documents, query OpenSearch (`_search`, `_knn_search`) to confirm BM25 and vector fields populate. Inspect Dify Flow logs for JSON validation errors. Use `docker compose logs retriever` / `ocr` / `unstructured` for runtime diagnostics.
- **中文：** 用示例文档测试流程，通过 OpenSearch (`_search`、`_knn_search`) 验证 BM25 与向量字段写入；检查 Dify Flow 日志捕获 JSON 校验错误；使用 `docker compose logs retriever`、`ocr`、`unstructured` 查看运行诊断。

## Operational Notes | 运维提示
- **EN:** Version and redeploy retriever when embedding models change (update dimensions + rebuild index). Persist volumes for OpenSearch and Unstructured caches. Consider rate limits/cache when calling Alibaba APIs; implement exponential backoff.
- **中文：** 嵌入模型变更时需更新向量维度、重建索引并重新部署 retriever。为 OpenSearch 与 Unstructured 缓存配置持久卷。调用阿里云 API 时注意限流与缓存策略，必要时加入指数退避。

