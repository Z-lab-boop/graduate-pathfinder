# 分路径报告契约

仅执行当前路径部分：保研 v0.1 用下节，考研 v0.2 用 [考研报告](#考研-v02-报告)。材料复核或展望另执行 [v0.3 契约](#材料复核与展望-v03-报告)，不改写原路径格式。不混合两类分组或把同名 reach 解释成同一计算规则。

## 保研 v0.1 报告

deep portfolio 的 report.md 必须按下列顺序，使用对应中文标题；缺资料的章节也保留并注明未执行原因。quick screen 可在聊天压缩同一逻辑；target comparison 不扩大发现范围。JSON 输入见 [案例契约](case-schema.md)，算法见 [决策模型](decision-model.md)，采证见 [来源规则](source-policy.md)。

1. **结论（outcome）**：具体入学年、保研轮次、候选范围、分析截至时间，推荐/暂定/待核验结果与当前可做的动作。排名只可在当前候选集合及权重配置下比较；不同集合、不同权重或不同刷新版本的 rank 不能直接比较。报告版本变化说明集合与权重变化。
2. **假设（assumptions）**：匿名档案、用户陈述与已确认事实、预计/确认资格、未知项；权重及维度尺度、负荷与硬约束。假设不得冒充确认资格。
3. **排除目标（excluded targets）**：每个 excluded 的 candidate_id、失败门槛、适用证据和原因；用户要求继续监控时仍保留失败状态。无排除项明确写无。
4. **申请组合（portfolio）**：reach/core/safety/monitor/excluded 分组均出现，可为空；每项给身份、分数/空值、rank/空值、资格、A–D、完整度、权重覆盖率。说明实际纳入/未纳入与负荷、方向、院校/轮次分散；monitor 不是可执行推荐。
5. **逐项目理由（target rationales）**：逐项说明适配/竞争位置、原始 dimensions、归一化权重、贡献、缺失项、分组输入、门槛依据、材料与准备缺口；区分导师方向相符与确认名额。列 sources 的 claim_id。
6. **证据警告（evidence warnings）**：关键缺失、过期、冲突、次级源依赖、年份适用性及审计 errors；分别展示资格、分数、置信度、完整度与覆盖率。A 不能替代本年适用性核验；页面不可访问不代表项目取消。
7. **敏感性（sensitivity）**：baseline_order/weights、delta=0.10 的逐维加减后归一化结果、赢家集合、stable/fragile/insufficient_candidates。若阈值存在，给 criterion、baseline_weight、weight、change、winner 及重分配权重；声明来自 0.01 网格，仅是偏好权重变化，不是精确连续临界值或招生因果效应。无阈值不是全局稳健证明；不足两个可排序候选不能宣称稳定。需要新增/移除候选或事实变化分析时另做明确情景重算，脚本不会自动完成这些情景。
8. **截止与冲突（deadlines/conflicts）**：原时区、截止原文、已确认精度、过期项、考核安排、重叠分钟/原时间和出行缓冲约束；未知时间及待核验项保留。若 ICS 生成，标明本地文件、包含/排除范围。
9. **下一步（next actions）**：按实际紧迫度列具体动作、责任人（默认用户）、依赖证据、期限/未知期限；需要官方澄清时给待询问题，不自动发送。
10. **来源（sources）**：每项 claim_id、对应目标/断言、可点击 source_url、标题、发布者、发布/检索日期、tier/status/scope；缺失占位说明检索入口与未找到项。按当前年份与历史资料分清适用范围，短引文遵守许可，不复制整页。
11. **边界声明（boundary statement）**：明确“分数、排名与分组用于当前候选集合及权重下的决策比较；不代表个人录取概率，safety 不保证录取。资格和日期以适用年份官方公告为准，未知与冲突仍需核验。本技能不自动提交、代投、联系导师或接受录取；申请者数据仅本地保存。”

### 保研 candidate-matrix.csv

UTF-8，第一行为固定列名，使用 CSV 转义；任何缺失值用空单元格，不能写成 0。数组/对象列用紧凑 JSON 文本；rank 空值只用于 monitor/excluded 或未评分。列顺序：

```text
candidate_id,institution,unit,program_code,program_name,research_track,degree_type,round,admission_year,status,eligibility,portfolio_group,weighted_score,rank,evidence_confidence,data_completeness,weight_coverage,deadline,failed_gates,unknown_critical_gates,normalized_weights,dimension_contributions,grouping_inputs,sources
```

已分析候选的 eligibility 必须取 `ranked[candidate_id]["eligibility"]`（门槛重算结果），不得取候选原始标签；例如原值 pass、confirmed fail 门槛应交付 fail/excluded。sources 来自候选的 claim_id，门槛数组来自 gate_evaluation，评分/分组列来自脚本结果；其余来自候选原记录。未分析时 eligibility 保留原值，并在报告明确其尚未由门槛重算；评分、权重覆盖和分组列留空，不能伪造脚本结果。含原始权重/维度依据的解释放报告并引用案例文件。若 CSV 将进入电子表格，防止来源文本被当作公式执行，同时保留本地 JSON 原值。

## 共享 refresh 的 changes.md

开头记录旧/新分析时间、候选范围、权重与来源复查范围；随后按 added / removed / changed / newly_conflicted / unavailable 分类（空分类写无）。每条含 candidate_id、claim_id 或字段、旧/新归一化值、来源、变化时间、影响门槛/置信度/分组及待办。删除仅指当前范围排除，旧证据与用户备注保留；无法访问单列 unavailable，不认定撤招。变化后重算再发布报告，禁止覆盖未核验用户状态。

机器验证、合成测试和行为清单复核各自标明范围；它们不证明真实录取、材料真实性或外部操作已完成。报告不能含真实申请者的敏感标识；公开示例只使用合成案例。

## 考研 v0.2 报告

deep shortlist 的 report.md 按下列顺序保留全部章节；unknown/未执行须注明原因。quick screen 可在聊天压缩，target comparison 只覆盖指定目标。计算输入与定义见 [考研流程](kaoyan-mode.md) 和 [阈值契约](threshold-semantics.md)；不使用保研 candidate-matrix 列、portfolio_group 或 safety。

1. **结论与当前项目身份**：明确入学年/考试年、截至时间、候选范围和本轮版本；逐目标列 candidate_id、学校、院系、专业代码/名称、方向、学位、regular-exam、学习方式、地区/类别和计划/人群。保留 current_catalog 的 claim_id 与本年核验边界，未知不填猜测。
2. **科目门**：用户与目标完整有序代码、status、differences（1 起位置）、switch_required、source_refs/reasons；愿意换科的用户声明与目标科目分数情景分别说明，不声称换科完成。
3. **分数情景**：用户区间与依据、year/scope/population/statistic/subject_codes、total/subjects，不生成预测分数；明确与现年或显式历史年份比较。
4. **分层阈值表**：每条原记录的 year/scope/身份限定/area/category/population/statistic/完整 subject_codes/total/subject_minimums/source_ref，comparisons 的 total_margin/subject_margins/status/descriptive_only/reasons。完整列 excluded_thresholds 及不兼容或缺证原因，不能挑低线。国家线不能当作专业线；已录取分布不能当复试线，各年不合并或外推未来线。
5. **历史波动**：逐年同口径原来源与缺口，historical_volatility 的 low/medium/high/unknown 和依据；口径变化、缺年、科目变化须明确，不用未知证明低波动。
6. **复试风险**：本年官方复试规则、考核内容/资格限制/计划等证据，retest_risk 的类别、理由与未核验项；分数 above 不证明资格或录取。
7. **适配与硬约束**：用户 fit_score 的 0–100 尺度与理由、地区/学习方式/预算/职业研究适配、换科成本及 gates 的有效状态与证据。completeness_basis 给分母与计数，data_completeness 不替代证据置信度或偏好权重覆盖率。
8. **证据置信度与风险带**：审计与声明中的较差 A–D、data_completeness、全部审计 errors/conflicts/过期/二手/未知。注明完整 evidence-audit.json 的 claims/candidate_summary/conflicts/errors 与审计时间；仅摘要不能确认当前关键字段。current_catalog 须与同 claim_id 的原审计 record 内容及值类型完全一致且有效/confirmed/无过期争议。列每目标 risk_band、reasons/source_refs/gate_evaluation，按考研流程明确 excluded/monitor/reach/match/conservative 的决策规则与未校准边界。
9. **敏感性**：本轮 candidate.sensitivity 的来源与完整 baseline_order/baseline_weights/scenarios/winner_set/stability/counterfactual_threshold；未执行原因保留。delta=0.10 与 0.01 网格阈值只表示偏好权重变化，无阈值不证明全局稳健，不足两目标不能称稳定。逐最高适配并列目标的赢家集合合并展示；分数、科目、候选/事实变化另列重算情景，不能冒称共享脚本已执行。
10. **Shortlist 与用户选择**：原样交付 `primary,decision_set,requires_user_decision,alternatives,monitor,excluded,reasons`，空列表与 null 均保留。只从 match/conservative 中按适配选择；唯一最高适配且 stable/winner_set 精确为该目标（若有 baseline_order 则首项一致）才给 primary；同分/fragile/缺敏感性给 decision_set，不用 ID 打破平局。reach alternatives、monitor 与 excluded 的原因保留，不把它们升级为可执行主目标。
11. **未完成官方核验与下一步**：逐 candidate_id/claim_id 给待查事实、真实官方入口、责任人（默认用户）、依赖与期限/未知期限；截止/日程原时区、精度和冲突说明，未知不写进 ICS。refresh 链接 changes.md，说明集合、用户区间、权重、规则和证据变化影响。
12. **来源**：逐 claim_id 列断言、可点击 URL、标题、发布者、发布/实际检索日、tier/status/effective_status/scope/applicable_admission_year；历史阈值来源必须支持当年的科目、全部身份与人群限定。本年科目来源不能替代历史适用性；机器审计不验证网页真实性。
13. **边界声明**：明确“科目门、分数区间的算术位置、风险带与 shortlist 用于当前证据和用户偏好下的择校比较，不代表个人录取概率。国家线、院校/院系/专业/方向线与已录取分布分别呈现，历史线不预测未来线；conservative 不保证录取。资格、目录、科目和时间以适用年份官方公告为准，未知/冲突仍需核验。本技能不自动提交、代投、联系导师或接受录取；申请者数据仅本地保存。”

### 考研 candidate-matrix.csv

UTF-8，标准 CSV 转义，空值留空，数组/对象使用紧凑 JSON；规则同保研表的公式防护与隐私要求。固定列顺序：

```text
candidate_id,institution,unit,program_code,program_name,research_track,degree_type,round,admission_year,study_mode,area,category,population,status,eligibility,risk_band,subject_match,score_scenario,historical_volatility,retest_risk,fit_score,evidence_confidence,data_completeness,sensitivity,current_catalog,thresholds,gate_evaluation,reasons,source_refs,sources
```

subject_match/score_scenario/risk_band/置信度等分析字段取 kaoyan-assessments.json 完整返回值；eligibility 取 gate_evaluation.eligibility，若科目 fail 导致提前 excluded、无 gate_evaluation，则写 fail 并以 subject_match 理由说明；未分析留空且报告注明未执行。其余身份/目录/原阈值取候选记录，缺失不补零。基础候选 status 不由分析自动推进。shortlist 固定字段另存 kaoyan-shortlist.json，不将 decision_set 缩成一名赢家。保存完整 evidence-audit.json；报告/表格不能替代其原始 claims。

## 材料复核与展望 v0.3 报告

材料复核/展望交付必须含以下五个文件。仅历史查询时也保留未执行部分及原因，不为填表编造申请者、资格或分数。文件存技能目录外的本地案例；考研科目/阈值结论仍取 v0.2 输出。原 v0.1/v0.2 报告与 CSV 契约保持适用，不新增或替换其固定列。

| 文件 | 必需内容 |
| --- | --- |
| `material-audit.md` | 分目标/逐要求的 requirement_id、必要性、来源 claim IDs、选定 document IDs、状态、blocking、缺条件、review_required；单列矛盾的各 claim ID/state/value 与同口径依据、未读页/OCR 不确定及待补件。完整不认证真实性，不代表已提交。原绝对路径不进入展示文本。 |
| `applicant-claims.json` | 六类状态的规范化数组：claim_id、field、value、state、source_document_ids、notes；签名/日期等文档观察带 scope=document。所有 ID 绑定本地清单；同口径冲突全保留，不选胜出值。只存必要学术字段，联系方式、身份证/学号、签名内容、家庭地址不写 value/notes。缺值保留 missing/null，不补零。 |
| `historical-cycle.json` | 明确当前年及选定历史七字段 scope；用于当前展望的历史入学年必须严格早于当前目标入学年。保留原归一化 events/counts、重建 timeline、calculate_stage_metrics 完整 scopes/metrics/rejected，包括未选 scope 的 scope_mismatch；日期两端/时区/精度、来源 URL/实际检索日/层级/claim IDs、排除与去重方法。只含 aggregate，不含名单行或身份。无证据保留空数组及缺口，不伪造零人。 |
| `admission-outlook.md` | 当前目标与入学年、分析时间、明确历史年/轮次；资格 eligibility、材料 packet_readiness、竞争 competitive_position、适配 program_fit（score/reasons）、证据 evidence_confidence 五项独立结果。缺少适配评分时 `program_fit.score` 为 null 并说明未评估，不能补零；真实 0 分仍保留。列完整历史 scope、阶段与分子/分母/描述性比率或拒算原因、uncertainties、缺失证据及 band_change_conditions 的最小可核验事实、各引用来源。未执行字段写“未执行/证据不足”及原因。 |
| `privacy-review.md` | 是否使用合成案例、原件未改写、生成文本脱敏 finding type/count/review_required/possible_over_redaction；人工复核状态（pending/completed）、误脱敏及遗漏检查范围、公开分享尚待条件。不得存匹配原文、片段、offset、签名图、来源绝对路径或真实身份。不得因正则通过宣称完全匿名。 |

本地输入另保留 materials-manifest.json、material-requirements.json、完整 evidence-audit.json；可保存 material-audit.json/admission-outlook.json 原函数返回值供复核。它们不是公开发布材料，原件、路径和必要私人观察严格留本地且受案例级 `.gitignore` 保护。检查已有文件，保留用户修改/旧版后再更新。

每份展望报告必须明确写：“历史阶段比例只描述对应历史范围，不代表个人录取概率；竞争档位是透明的序数判断，不保证录取。资格、材料、竞争位置、适配和置信度分别解释，材料可见不认证真实性。本次交材料仅为本地复核，未进行外部提交。”竞争档位使用 strong/competitive/borderline/weak/evidence_insufficient；与保研 reach/core/safety 或考研风险分组分别呈现。band_change_conditions 是可能改变判断的待核验事实，不承诺补件后录取改善。

对生成 Markdown、CSV 展示文本及准备分享的 JSON 文本先执行 redact_text；原始文档从不经过改写。结构化学术字段不能被粗暴脱敏破坏类型，应从采集阶段省去敏感字段，并检查规范化值/notes/source metadata；仍有敏感内容则交付脱敏副本且保留本地证据关系。脱敏 findings 仅存数量/类型/复核标志。公开结果去掉路径、真实标识及可识别组合，人工复核未做如实写 pending；合成测试和自动检查不能代替该复核。
