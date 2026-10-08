# v0.2 考研阈值与科目契约

本模块仅处理已校验的 profile/candidate 基础字典上的扩展；不改变保研门槛、排名或录取语义。例子及测试数值均为合成数据，不代表真实招生。

## 阈值含义

| scope | 含义 | 合成例子 |
|---|---|---|
| national | 对指定地区、学科类别、人群的国家层面要求 | 2026 年 A 区某类别普通考生总分 264 |
| institution | 学校整体公布的要求 | 虚构甲大学普通考生总分 280 |
| unit | 指定院系公布的要求 | 虚构甲大学计算院普通考生总分 290 |
| program | 指定专业公布的要求 | 同院 085400 专业普通考生总分 300 |
| direction | 指定专业内研究方向的要求 | 同专业“透明系统”方向总分 310 |
| admitted_distribution | 特定已录取人群的描述性分数统计 | 2025 年该专业普通批已录取者初试总分中位数 325 |

国家线不能当作专业线；专业代码出现在国家线记录中，也不会改变其层级。学校线不能覆盖院系线；已录取者最低值、中位数、均值也不能转换成复试线或未来录取门槛。录取分布必须指定 statistic（如 minimum/median/mean 或其他明确命名的统计量），并明确人群；它仅产生描述性比较。跨年份不合并、不平均、不外推。没有公布的未来线保持 insufficient_evidence。

## 科目扩展

profile.subject_combination 和 candidate.subject_combination 均为 `{codes: ["101", "201", "301", "408"], evidence: [证据记录]}`。codes 必须为非空字符串序列；按顺序做 Unicode NFKC 与首尾空白归一化，保留前导零；不按显示名称、子字符串或集合匹配。证据 value 必须给出同一完整代码序列。

嵌入的 evidence 记录复用 v0.1 全部必需字段，另需 applicable_admission_year 整数。科目证据需与双方 admission_year 相同；candidate 的证据 candidate_id 需匹配目标。profile 可引用确认其备考组合所依据的官方科目方案。用户决定备考哪些科目仍是用户事实，不能由本模块生成。

current official 的可计算定义：v0.1 结构有效、T1/T2、status=confirmed、适用年份一致，在 profile.audit_at 时 retrieval 日龄 0..365 天，published_at 不晚于审计日；若带 effective_status/stale/conflict_groups 则不得标示过期或冲突。audit_at 为带时区 ISO 时间；缺省使用当前 UTC。时效规则沿用 v0.1 审计日历日口径，来源真实性、官方发布者身份仍需采证者核实。缺失、过期、二手、错误适用年份、错误值、任何混入的争议记录均导致 unknown，不挑选有利证据。

profile.preferences.willing_to_switch_subjects 必须为字面布尔 true 才能接受已确认的科目差异。否则确认不匹配为 fail；完全匹配为 pass。愿意切换不修复 unknown，也不证明已完成切换。输出保留 profile_codes/candidate_codes、1 起位置的 differences、switch_required、source_refs 与 reasons。

## 阈值扩展

candidate.thresholds 为数组，每条必需 year（正整数）、scope（上表值）、total（有限非负数）、source_ref（非空 claim_id）。可选 subject_minimums 为代码到有限非负最低分的映射，population 为明确人群字符串，statistic 为描述性统计名。代码归一化后重复的单科键拒绝，原始键和值保留在输出，不覆盖用户数据。

identity 字段可含 institution/unit/program_code/research_track/degree_type/round/area/category。comparison 按 scope 要求：institution 需学校一致；unit 需学校及院系一致；program 需再加专业代码；direction 需再加 research_track；admitted_distribution 至少学校、院系、专业一致。其他已给定身份限定同样必须匹配 candidate；national 的地区、学科类别及计划限定须在 population 与 area/category 明示。所有比較都要求 population 非空且与请求完全一致。

classify_threshold 只校验形状，返回原记录深拷贝及 is_program_specific/descriptive_only。is_program_specific 仅 program/direction 为 true，不靠字段名猜测层级。它不校验来源真实性，不声称分类记录可用于决策。

实际比较时，每条 threshold.evidence 为 v0.1 证据记录，claim_id 等于 source_ref，candidate_id 匹配目标，applicable_admission_year 等于 threshold.year，且满足上述 current official 规则。evidence.value 必须完整支持阈值事实对象：year/scope/total/population/statistic/subject_minimums 与已给身份限定；这些键双方一致，不能丢弃来源中的单科最低分或人群限定。source_ref/evidence 外壳及其他备注不参与值比较。

## 分数情景扩展和输出

profile.score_scenario 为 `{year: 2026, scope: "program", population: "普通考生", total: [310, 330], subjects: {"101": [50, 60], "201": [50, 60]}}`。year 为明确请求比较的年份（可显式请求历史年份），scope/population 必须与记录相同；admitted_distribution 另需同名 statistic。数组须恰为两个有限非负数，low <= high，bool 不算数值。范围来自用户，不生成预测分数。

subject_codes 可显式给出该分数情景适用的完整科目序列，缺省为 profile 的已确认组合。科目门必须 pass，且 scenario 序列必须与 candidate 确认的序列完全匹配。愿意切换但未明确给出目标科目的情景，不沿用旧组合的分数。阈值中的单科代码必须属于该组合。subjects 按准确代码键查询，每个有公布最低分的科目都需用户范围；不存在的范围不补零、不推测。

compare_score_scenario 返回 status、comparisons、excluded_thresholds、reasons，以及可用时 subject_match。每个 comparisons 项保留完整已分类 threshold（含年/层级/人群/统计名/来源），total_margin、subject_margins、status、descriptive_only、reasons；excluded_thresholds 保留原始或已分类记录及不兼容/无证据原因，不丢历史记录。

margin 为 `[low - line, high - line]`。全部区间下界严格高于对应阈值为 above；任一完整区间上界低于阈值为 below；其余为 overlaps，包括等于阈值。缺失任何公布的单科范围为 insufficient_evidence。多个兼容记录逐条比较；结果不一致时总状态为 insufficient_evidence 并注明冲突，不挑最低线。以上状态只说明分数区间的算术位置，不能解释为资格、复试保证、录取概率或录取结果。资料收集和报告仍须保留每条原来源及真实核验边界。

验证：`python3 -m unittest tests.test_assess_kaoyan -v`。
