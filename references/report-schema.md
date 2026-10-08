# v0.1 报告契约

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

## candidate-matrix.csv

UTF-8，第一行为固定列名，使用 CSV 转义；任何缺失值用空单元格，不能写成 0。数组/对象列用紧凑 JSON 文本；rank 空值只用于 monitor/excluded 或未评分。列顺序：

```text
candidate_id,institution,unit,program_code,program_name,research_track,degree_type,round,admission_year,status,eligibility,portfolio_group,weighted_score,rank,evidence_confidence,data_completeness,weight_coverage,deadline,failed_gates,unknown_critical_gates,normalized_weights,dimension_contributions,grouping_inputs,sources
```

已分析候选的 eligibility 必须取 `ranked[candidate_id]["eligibility"]`（门槛重算结果），不得取候选原始标签；例如原值 pass、confirmed fail 门槛应交付 fail/excluded。sources 来自候选的 claim_id，门槛数组来自 gate_evaluation，评分/分组列来自脚本结果；其余来自候选原记录。未分析时 eligibility 保留原值，并在报告明确其尚未由门槛重算；评分、权重覆盖和分组列留空，不能伪造脚本结果。含原始权重/维度依据的解释放报告并引用案例文件。若 CSV 将进入电子表格，防止来源文本被当作公式执行，同时保留本地 JSON 原值。

## refresh 的 changes.md

开头记录旧/新分析时间、候选范围、权重与来源复查范围；随后按 added / removed / changed / newly_conflicted / unavailable 分类（空分类写无）。每条含 candidate_id、claim_id 或字段、旧/新归一化值、来源、变化时间、影响门槛/置信度/分组及待办。删除仅指当前范围排除，旧证据与用户备注保留；无法访问单列 unavailable，不认定撤招。变化后重算再发布报告，禁止覆盖未核验用户状态。

机器验证、合成测试和行为清单复核各自标明范围；它们不证明真实录取、材料真实性或外部操作已完成。报告不能含真实申请者的敏感标识；公开示例只使用合成案例。
