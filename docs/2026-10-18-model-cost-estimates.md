# 文本模型调用成本估算与价格维护

## 用户看到什么

学生资源页、教师知识页、管理员检索测试的“AI 用量”增加费用估算。显示已估算/未估算调用数、各币种金额或区间，以及未估算原因。金额属于平台模型调用成本，不是用户应付费用；缺失用量、失败/中断、旧记录、未知模型或渠道都不会被计作免费。

经典与漫画主题仍用各自变量。页面以十进制字符串展示，保留低于一分的非零金额，不将其四舍五入成 0.00。不同币种不相加、不换算。不加载或返回对话正文、密钥或用户逐人消费明细。

## 已核对的公开价格

核对时间为 2026-10-18，价格单位均为每百万 tokens。这里只是公开单价，不含赠金、税费、协议折扣、代理加价及基础设施费用。

| 官方接口与响应模型 | 未缓存输入 | 缓存输入 | 输出 | 币种 |
|---|---:|---:|---:|---|
| api.deepseek.com / deepseek-flash | 0.15–0.30 | 0.003–0.006 | 0.60–1.20 | USD |
| api.openai.com / gpt-4o-mini、gpt-4o-mini-2024-07-18 | 0.15 | 0.075 | 0.60 | USD |

DeepSeek 发布峰谷价格及适用时段；本实现保留其上下界，不推测节假日或供应商最终计费时刻，也不把请求别名 deepseek-chat 自动当成已报告的响应模型。[DeepSeek 价格来源](https://api-docs.deepseek.com/quick_start/pricing/)

OpenAI 条目仅覆盖上述模型的标准文本调用与已核实的模型快照；其他模型、服务档位、缓存写入等项目需要独立核对，不能套用此行。[OpenAI 模型价格来源](https://developers.openai.com/api/docs/models/gpt-4o-mini)

内置价格文件：`backend/app/data/model_rates_v1.json`。`verified_at`/`effective_from` 是本地核对并启用时间，**不是声称供应商从该时刻改价**。本版复核截止为 `2026-10-25T00:00:00Z`，到期后新调用不再套用过期价格，已有快照保持不变。有效期是本系统的维护窗口，并不保证供应商在窗口内不改价。

## 计算方法与未知信息

每次实际文本模型 HTTP 尝试开始时读取并冻结价格表，结束时以响应报告的实际模型、可信接口主机、默认服务档位和用量匹配。输入、输出分别计价，缓存输入是输入的一部分，思考 tokens 已包含在输出数量中，不重复相加。DeepSeek 的缓存命中/未命中字段和 OpenAI 兼容 cached_tokens 会核对一致性。[DeepSeek 用量字段](https://api-docs.deepseek.com/api/create-chat-completion/)

已知缓存数量时，对每个价格边界使用：

`金额 = ((输入 − 缓存命中) × 未缓存输入单价 + 缓存命中 × 缓存单价 + 输出 × 输出单价) / 1,000,000`

缓存拆分未返回、但输入和输出完整时，下界按全部输入命中缓存，上界按全部未命中缓存，保存 `cache_split=unknown_bounded`；不将缓存缺失默认为零。输入或输出缺失、total 不一致、负数/布尔值计数、缓存字段冲突，则不计算金额。

只有支持的纯文本 Chat Completions、成功结束且模型已报告的调用可估算。带工具、非文本内容、预测输出、音频、独立缓存写入、其他服务档位与其他端点保持未估算。失败/取消/流中断可能已产生费用，但没有账单核对依据时不推断为零。代理或同名模型必须与明确核对的接口主机匹配，不能拿官方价格冒充代理收费。

金额以 Decimal 运算，单次记录保存 NUMERIC(20,10)；下界向下、上界向上保留 10 位，避免舍入把范围缩窄。聚合按币种和工作流分别进行，保留未估算次数与原因。它不是账户余额、实际发票金额或付费结算系统。

## 数据与接口

迁移 `20261018_0033` 为 `ai_model_calls` 新增可空字段：

- cached_input_tokens；cost_status；cost_currency；cost_min/cost_max；price_snapshot。
- 快照包含条目编号、版本/哈希、来源、有效期、价格区间、实际匹配模型及缓存口径。
- 历史字段保留 null，不用今天的价格补算过去，也不回填不存在的用量。
- 账本仍不保存提示/回答/密钥。价格文件读取或校验失败仅使本次费用未知，不阻断模型调用。

现有 GET `/api/v1/ai/usage` 与 GET `/api/v1/teacher/classes/:class_id/ai-usage` 保留本人/当前班级权限，新增 `cost_estimate`：

- status：no_calls / unpriced / partial / estimated。estimated 代表所记录调用均具备估算，可包含价格区间，不代表实际账单金额。
- basis=published_rates_estimate、invoice_verified=false、estimated_calls、unpriced_calls。
- by_currency：currency、min/max（十进制字符串）、calls、range_calls。
- unpriced_reasons：原因与次数；by_workflow：各工作流同口径统计。

原 `cost` 仍为 null（没有已核对实付金额），`cost_status` 为 estimate_available 或 not_priced。没有调用时不生成虚假的 USD 0 账单。原 `/student/tutor/usage` 继续只展示其既有配额/调用统计，统一金额见 `/ai/usage`。

## 如何维护价格

1. 打开供应商官方价格页及实际账号合同，核对接口、**响应模型名**、服务档位、币种、缓存与输出计费方式。第三方代理不得直接复制官方渠道条目。
2. 更新条目 id、card version、核对时间和新的有效区间；保持旧已记录快照不动。单次调用开始前捕获表版本，文件在调用期间变更也不影响它。
3. 使用后端命令验证，不会请求供应商或产生费用：

   ```powershell
   ../.venv/Scripts/python.exe scripts/check_model_rates.py
   ```

4. 可通过 `AI_MODEL_RATE_CARD_FILE` 指定服务器管理的 JSON 文件（建议绝对路径）；默认使用内置文件。自定义表应保留需要的所有条目，文件变更影响后续调用，不需重启。不得通过业务 HTTP 请求传入价格。配置损坏、价格条目重叠、缺失或过期时不回退到猜测价格。
5. 自定义文件用 `scripts/check_model_rates.py --file <path>` 检查。当前校验器仅覆盖本方案的“输入/缓存输入/输出”价格模型；要增加复杂服务档位或其他计费项目，应先扩展契约和测试。

`check_model_rates.py` 返回非零代表无有效条目、过期或校验失败。核验窗口届满须重新查看价格；不是把 valid_until 机械延后就完成复核。

## 验证与限制

- SQLite 成本/账本专项 41 项通过；成本、原账本、RAG、辅导运行控制、资源接纳相关回归 77 项通过：`output/plex-p4-pricing-tests.log`、`output/plex-p4-pricing-regression.log`。最后价格重叠与非法档位补测见 `output/plex-p4-pricing-final.log`；这些重复测试不累加。
- 临时独立 MySQL 成本/账本专项 41 项通过、364 项未选中，含迁移重复、历史空值、并发身份和币种/班级汇总：`output/plex-p4-pricing-mysql.log`。
- 前端行为与费用组件 SSR 展示 17 项通过，构建、类型、生产文案和包预算通过：`output/plex-p4-pricing-frontend.log`、`output/plex-p4-pricing-build.log`。SSR 验证不能替代浏览器视觉走查。
- 实际 HTTP/外部模型在隔离 SQLite 与合成课程中验收：DeepSeek Flash 报告 970 tokens，估算 USD 0.000250602–0.000501204。脚本独立核对公式、价格来源/哈希及 API 汇总，重放/恢复不增加调用或估算金额；仍复核配额与来源撤回。记录：`output/plex-p4-pricing-live.json`。
- 重现：后端执行 `../.venv/Scripts/python.exe scripts/check_rag_runtime.py --real-model --verify-pricing --output ../output/plex-p4-pricing-live.json`。该命令会进行真实付费 API 调用，但仅使用隔离合成资料；未匹配价格或价目表过期时验收失败，不伪装成已核算。

尚未做供应商账单对账，没有计算“每次有效帮助成本”或“每道已发布题成本”，因为其分母还需要实际效果/采用数据。真实教师标注、目录执行复验、教师审核与用户试用继续按完整方案推进；浏览器视觉验收仍未完成。

主库无活动请求后严格升级至 20261018_0033 并重启后端；健康、前端、本人/班级费用契约及 401/403 权限检查通过，见 `output/plex-p4-pricing-http.json`。没有主库业务测试写入。
