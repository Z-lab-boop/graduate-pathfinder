# 候选门槛、决策评分与申请组合

本模型用于保研申请目标比较，不预测录取结果。输入为已验证候选记录，附加
`gates`、`dimensions`、`evidence_confidence` 与 `data_completeness`。
排名与分组必须同时呈现门槛状态、证据置信度、权重覆盖率及分组输入。

## 门槛语义

每条门槛格式为 `{gate_id, status, critical, evidence_status}`。
`gate_id` 是候选内唯一非空字符串；`status` 为 `pass`、`fail`、`unknown`；
`critical` 是布尔值；`evidence_status` 为 `confirmed`、`secondary_only`、
`conflicted`、`stale`、`missing`、`not_applicable`。

只有 `confirmed` 的 pass/fail 能确认通过或失败。其他证据状态均使该门槛
保持 unknown；不适用项应在上游确认后不作为门槛输入。任意 confirmed fail
使资格为 fail 并分入 excluded，即使另有未知门槛。不存在失败但关键门槛未知，
资格为 unknown，分入 monitor。没有关键门槛（包括空列表）无法确认资格，
也保持 unknown。非关键 unknown 不阻断其他已确认关键门槛。

输出 `gate_evaluation` 保留原状态、有效状态、失败门槛及未知关键门槛。
原候选的资格标签不能覆盖门槛计算结果。调用方负责覆盖所有适用关键要求；
函数无法检测被遗漏的真实招生要求。

## 维度、权重与缺失值

允许维度均为有限数值，范围为 0–100；布尔值、字符串、null、NaN、无限值
不合法。缺失项直接不提供键，不能补零。

| 维度 | 明确含义与输入依据 |
|---|---|
| competitive_position | 申请者相对目标公开要求和可核验竞争背景的位置，由用户明确给定并记录理由；数值越高表示相对位置越有利 |
| research_fit | 研究兴趣、已完成工作与项目方向的匹配，由用户根据具体方向和经历给定 |
| academic_match | 课程、学科基础与培养要求的匹配 |
| career_fit | 培养路径与用户职业目标的匹配 |
| location_fit | 地点与用户实际偏好的匹配 |
| cost_fit | 培养及生活成本与用户预算的匹配 |
| application_readiness | 所需材料、能力准备与申请进度的完成程度 |

机构名气、院校层级不能直接用作竞争位置或分组依据。维度评分需要用户提供
尺度和依据；这些值不由程序从学校名称或历史比例推算。维度可以不加权，
但仍须合法。分组使用的两个维度须明确给定，允许其权重为零。

用户权重可任意比例给定，每项须非负有限数值，总和须为正。归一化后权重
总和为 1。未列入权重的维度不参与分数。零权重维度不增加覆盖率。

`weight_coverage` = 已提供维度的归一化权重之和。
`dimension_contributions` = 各已提供且列入权重维度的数值 × 归一化权重。
`weighted_score` = 所有贡献之和 / weight_coverage。
贡献表示除以覆盖率前的分子项，覆盖率不足 1 时，其和不等于最终分数。
无正权重维度可用时，分数为 null，覆盖率为 0。缺失维度不出现在贡献中。

`data_completeness` 是上游数据完整度（0–1），保留展示，不能作为得分或
权重覆盖率的替代值。置信度 A–D 来自证据审核，独立于分数。

## 分组与排名规则

以下阈值是 v0.1 的显式工作规则，并非从真实录取结果拟合出的统计模型。
任意资格 fail → excluded；资格 unknown、证据置信度 D 或权重覆盖率
小于 0.70 → monitor。符合上述条件后，若缺少 competitive_position 或
research_fit，或 research_fit 小于 60，也分入 monitor。

对资格 pass、置信度 A/B/C、覆盖率至少 0.70、研究匹配至少 60 的目标：

| competitive_position | 分组 |
|---|---|
| 小于 50 | reach（冲刺） |
| 至少 50 且小于 80 | core（核心） |
| 至少 80 | safety（相对保守） |

这些标签描述申请组合的相对定位。safety 不保证录取；B/C 的证据局限仍应
展示和复核。分组输入在 `grouping_inputs` 中保留。
`rank_candidates` 返回候选 ID 为键的字典。reach/core/safety 按决策分数
降序排名，同分按 candidate_id 字符串升序，rank 从 1 连续递增。
monitor/excluded 的 rank 为 null，不参与排序；其诊断分数仍可见。
重复或空候选 ID 不合法。字典顺序不承担排名含义，后续分析应读取 rank。

## 合成计算示例

以下仅为算法演示，不对应真实学校或申请者。权重设为 competitive_position=3、
research_fit=2、career_fit=5，归一化为 0.3、0.2、0.5。
前两项分别为 65、80，career_fit 缺失：覆盖率=0.5；贡献为 19.5 和 16；
最终分数=(19.5+16)/0.5=71。即使资格已确认通过且置信度 A，覆盖率不足
0.70，仍分入 monitor，没有排名。career_fit 不作为 0 分参加计算。

若用户将权重明确改为 3、2，只比较这两个维度，则归一化为 0.6、0.4，
贡献为 39、32，覆盖率为 1，分数为 71；在已确认通过且置信度 A 的前提下，
位置 65、匹配 80 对应 core。权重选择变化必须在报告中显示。

## 历史比例与个人结果

历史入选比例是某年、某项目、某轮次、明确分母下的群体描述。它受样本选择、
申请池差异和规则变化影响。不得将该比例转换为个人录取概率，也不得将本模型
0–100 的决策分数写成录取百分比。报告应分别展示历史事实、用户偏好评分、
证据局限与待核验事项。
