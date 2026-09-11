# cn-model-gateway

Source repository: [fyniujin/devskill](https://github.com/fyniujin/devskill)

Canonical key: `fyniujin/devskill:cn-model-gateway`

Manifest: [https://github.com/fyniujin/devskill/blob/main/cn-model-gateway/SKILL.md](https://github.com/fyniujin/devskill/blob/main/cn-model-gateway/SKILL.md)

## Description

国产大模型统一 MCP 服务器，通过标准 JSON-RPC 2.0 协议为 Claude Code / Cursor / Cline / n8n 等 18+ Agent 框架提供 DeepSeek、通义千问、智谱 GLM、Kimi、腾讯混元、火山豆包、MiniMax、零一万物、百川智能、阶跃星辰十家模型的统一调用接口。新增 5 个非 MCP 框架适配器：LangChain Tool、AutoGPT Plugin、CrewAI Tool、Coze 插件、Dify 工具节点，实现从 MCP 生态到全 Agent 生态的扩展。内置模型性能基准测试套件（50 道题库、6 维度评分、雷达图对比、历史追踪）和 Token 价格实时追踪（价格抓取、变更通知、趋势图、成本预测）。支持 8 个 MCP 工具（ask_model/describe_image/embed_text/rerank/audio_transcribe/video_understand/list_providers/health_check）、资源读取（配置/使用统计）、预置 prompt 模板（代码审查/翻译），内置统一错误映射、流式 SSE 输出、使用量统计、硬件感知并发控制。auto 模式支持能力画像排序 + 自动故障转移（超时/失败切备用）；API key 支持环境变量优先读取；SQLite 启用 WAL 模式支持多 Agent 框架并发写入；支持多模态视觉模型（Qwen-VL/GLM-4V/豆包视觉）和图片理解（describe_image）；支持 Function Calling / Tool Use（ask_model 传入 tools 参数）；新增文本向量嵌入（embed_text）、文档重排序（rerank）、语音转文字（audio_transcribe）、视频理解（video_understand）四个新工具。config.json 填写 api_key 即可启动，无需 GPU、不做微调、不做私有部署，只做标准 MCP 协议网关。

## Classification

Categories: ai-ml, content, devops, engineering, integrations, media
Client compatibility: not explicitly detected
License: MIT

## Resources

Scripts: 0
References: 0
Assets: 0
Other: 4

## Scores

Overall: 97
Quality: 93
Security: 100
Maintenance: 100
Adoption: 10

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-11T12:41:20.921780+00:00
Published: 2026-09-11T16:55:08.871829+00:00
Publication event: add
Source fingerprint: `e6d93d577acd09a6bbf397e61f7510ea4dc45ed200355d54ed1db79bac6253b8`
Analysis fingerprint: `6090d27b0811c05b974b23eb97b2650b543cd16459668dabaa30f5255f1797bf`
