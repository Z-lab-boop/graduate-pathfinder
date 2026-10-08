# v0.1 本地案例契约

编码 UTF-8，JSON 禁止 NaN/Infinity。skill_root 外的用户目录或 `./graduate-pathfinder-cases/<case-label>/`；case_label 是匿名、安全单目录标签，不含路径分隔符、`.` 或 `..`。解析路径与符号链接后验证边界。仅用户要求持久化/文件交付时创建；技能仓库仅合成测试。

必需文件：profile.json 对象、candidates.json 数组、evidence.json 数组。deep portfolio 另需 report.md 与 candidate-matrix.csv，格式见 [报告契约](report-schema.md)。refresh 另需 changes.md；events.json、deadlines.ics 和脚本审计/排名/敏感性/冲突 JSON 为按需输出。无材料审阅或考研 v0.2 实现。

建案例级 `.gitignore` 默认忽略 `*`，可保留 `!.gitignore`；用户明确选择版本管理后才调整。报告、CSV、分析结果同样可能有隐私，不能只忽略原始证据。任何公开产物脱敏，不写学号、证件号、电话、私人邮箱、签名、印章或第三人资料。避免覆盖用户已有案例与备注。

## 脚本校验的必需键

以下每行的键必须存在，包括允许 null 的键；额外键不会被基础校验器检查。工作流的年份一致性、唯一 ID、交叉引用、路径标签、适用周期与下面扩展字段须人工核验，不声称 JSON 校验器覆盖它们。

### profile.json

| 键 | 类型/允许值 |
|---|---|
| case_label | 非空字符串 |
| pathway | baoyan / kaoyan；v0.1 流程只执行 baoyan |
| admission_year | 整数，明确入学年份；不能是布尔值 |
| preferences | 对象，初筛可为空；深度排序需要 criterion_weights |

### candidates.json 每条记录

| 键 | 类型/允许值 |
|---|---|
| candidate_id | 非空字符串，案例内唯一稳定 ID，覆盖完整目标身份 |
| pathway | baoyan / kaoyan |
| admission_year | 整数，与 profile 一致 |
| institution, unit, program_name | 各为非空字符串 |
| program_code, research_track | 各为非空字符串或 null（未知） |
| degree_type | academic-master / professional-master / direct-phd |
| round | summer-camp / pre-recommendation / september / regular-exam；v0.1 不执行 regular-exam |
| deadline | 带时区 RFC3339，含秒如 2027-06-15T17:00:00+08:00，或 null；基础校验允许小数秒，日程模块不允许 |
| status | discovered / verified / preparing / submitted / screened / assessment / offer / waitlist / rejected / withdrawn / pending-official-system / accepted |
| eligibility | pass / fail / unknown，排名时以 gates 重算结果为准 |
| evidence_confidence | A / B / C / D，来自审计与适用性检查 |
| data_completeness | 有限数值 0–1；不得用它代替权重覆盖率 |
| sources | 数组；工作流约定存 evidence.json 的 claim_id，基础校验只检查数组类型 |

身份包含 institution/unit/program_code/program_name/research_track/degree_type/round/admission_year/pathway，不能按校名合并。status 的上述全部值是合法枚举，并非所有状态都必按线性顺序经历；每次进展附用户/官方事实，不能自动推进。

### evidence.json 每条记录

| 键 | 类型/允许值 |
|---|---|
| claim_id, candidate_id | 非空字符串；claim_id 案例内唯一，candidate_id 引用候选 |
| field | 非空字符串，无固定 enum；审计关键字段为 eligibility/deadline/program_availability/degree_type |
| value | 必须存在，可为任意 JSON 值含 null；关键 null 通常不构成可用覆盖 |
| source_url, source_title, publisher, short_evidence | 各为非空字符串；URL 和发布者标签须采证者核实 |
| published_at | YYYY-MM-DD 或 null |
| retrieved_at | 带时区 RFC3339，含秒 |
| tier | T1 / T2 / T3 / T4 |
| status | confirmed / secondary_only / conflicted / stale / missing / not_applicable |
| scope | school / program / round |
| conflict_group | 非空字符串或 null；限定同候选同周期同要求，跨来源统一命名 |

参见 [来源规则](source-policy.md) 的出处、时效与冲突规则。证据本身没有必需 admission_year 键；工作流必须逐条检查适用年份，可附 applicable_admission_year（整数或 null）与 cycle_note（字符串）。同 claim_id 内容变化保留旧记录/快照，刷新不能丢弃争议源。

## 工作流扩展：档案、权重和评分

基础 JSON 允许最小档案；下列是流程约定而非新增脚本校验。最小筛选要问到所需字段，未知允许 null：

- profile.current_institution/current_major/research_interests：字符串、字符串、字符串数组或 null。
- profile.academic_rank：对象 `{numerator, denominator, policy, as_of}` 或 null；前两项正整数或 null，policy 字符串或 null，as_of 为 YYYY-MM-DD 或 null。
- profile.gpa：对象 `{value, scale}` 或 null；value 有限数值或 null，scale 字符串或 null。
- profile.language_evidence：数组 `{test, result, as_of, basis}` 或 null；字符串字段可 null，as_of 日期或 null，basis 标明用户陈述/可核验出处。
- profile.recommendation_eligibility：对象 `{state, basis, finalization_date}`；state 为 expected / confirmed / unavailable / unknown；basis 为字符串或 null，finalization_date 日期或 null。
- preferences.degree_types：上述 degree_type 数组或 null；locations 为字符串数组或 null；budget 为 `{amount, currency, period}` 或 null（amount 非负有限数值或 null，后两项字符串或 null）；career_goal 字符串或 null；hard_constraints 字符串数组或 null。

深度组合还要求 preferences.risk_tolerance（用户文字或 null）、max_applications（正整数或 null）、travel_constraints（字符串数组或 null）。未知负荷则只给暂定组合，不声称可执行。

排序必需 preferences.criterion_weights：非空对象，键仅限 competitive_position、research_fit、academic_match、career_fit、location_fit、cost_fit、application_readiness；值非负有限数值且至少一项正值。允许缺维度和零权重；脚本归一化。

排序候选还必需：

| 键 | 契约 |
|---|---|
| gates | 数组，每条必须 gate_id（候选内唯一非空字符串）、status（pass/fail/unknown）、critical（布尔）、evidence_status（证据 status 枚举）；可为空但不能确认资格 |
| dimensions | 对象，键仅为上述七个维度；值为有限数值 0–100；缺项省略，不能 null/零填补未知 |
| gate_bases | 对象，gate_id → claim_id 数组及/或已脱敏用户硬约束说明；人工检查每条门槛依据 |
| dimension_bases | 对象，维度名 → 用户给定尺度、理由及证据说明字符串；不可由学校名推造 |

gate_bases/ dimension_bases 是报告所需解释，rank_candidates 不校验它们。data_completeness 同时记录 completeness_basis（所选决策字段、分母与计数说明字符串）；不可凭空给百分比。可选 achievements 为用户陈述经历数组，supervisor_contact_state 为用户事实字符串，user_notes 为字符串，deadline_notes 为原文/精度/来源说明字符串，status_basis 为用户或官方进展说明字符串。真实状态更新时 status_basis 必需。

## 日程与脚本结果

events.json 为数组。每条必需 candidate_id、event_type（非空字符串，无 enum）、start、end（带显式 offset 的 ISO 时间，可分钟或秒，不接受小数秒），且 end > start。precision/date_precision/deadline_precision 若给定只能 exact；默认已明确时间。summary/description/location 为可选字符串；calendar 文本拒绝非法控制字符。工作流额外给 source_claim_ids 数组或 user_basis 字符串说明依据。不明时间留在报告，不能塞入 events。

ranked-candidates.json 为 ID → 对象，保留 candidate_id、eligibility、gate_evaluation、evidence_confidence、data_completeness、normalized_weights、dimension_contributions、weight_coverage、weighted_score（数值或 null）、grouping_inputs、rank（从 1 起整数或 null）、portfolio_group（reach/core/safety/monitor/excluded）。gate_evaluation 含 eligibility、failed_gates、unknown_critical_gates、gates（另含 effective_status）。详情见 [决策模型](decision-model.md)。

evidence-audit.json 顶层为 claims、candidate_summary、conflicts、errors；不丢弃原记录与错误。sensitivity.json 顶层为 baseline_order、baseline_weights、scenarios、winner_set、stability（stable/fragile/insufficient_candidates）、counterfactual_threshold（对象或 null）；阈值 effect 仅 decision_weight。schedule-conflicts.json 是冲突对象数组，含 candidate_ids、event_types、overlap_minutes、local_timestamps。保留脚本完整返回值，不当作另一套招生事实。

## 验证边界

```bash
python3 scripts/validate_case.py /absolute/local/case --skill-root /absolute/skill/root
```

成功只证明三个基础输入的结构及案例路径边界。它不验证事实、年份对齐、ID 唯一性、链接真实性、扩展字段、材料真实性或提交状态。完整工作流还需人工检查出处/交叉引用，调用 [保研流程](baoyan-mode.md) 的审计、门槛、排序、敏感性及日程函数。
