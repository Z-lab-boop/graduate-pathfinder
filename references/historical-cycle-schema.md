# 历史轮次事件与阶段计数契约

历史资料只支持对应年份与口径的描述，不预测本年流程或个人录取概率。处理入口为 `scripts.calculate_historical_metrics` 的 `scope_key(record)`、`reconstruct_timeline(events)` 和 `calculate_stage_metrics(counts)`；三个接口均无文件写入、联网或自动抓取行为。

## 每条记录的精确身份与证据

固定 scope key 顺序：`(admission_year, institution, unit, program_code, degree_type, research_track, admission_round)`。`admission_year` 为正整数（拒绝 bool）；其余为明确非空字符串。代码不去空格、合并别名或推断缺项，专业代码保存字符串以保留前导零。未确定范围不得改用宽泛院校范围；未知字段需补证后方可计算。确实不适用的方向以源资料支持的明确标签表示，不能拿“未知”当通配符。

每条 normalized record 包含 `claim_ids`：非空证据 ID 字符串数组。采证时必须同时保存 `source_url`、`retrieval_date`（实际检索 ISO 日期）、`evidence_tier`（项目 A–D）、`method_notes`（无身份信息的计数/日期核对说明）。脚本允许这四个字符串元数据省略以接收已有证据索引，输出保存已给字段；调用者必须确保 claim IDs 可定位上述元数据，缺来源资料不能当作已核验。脚本只验证结构和算术，不认证来源真实性。

Normalized records 和结果禁止姓名、学号、申请者编号或名单行；`name/names/student_id/student_ids/student_number/student_numbers/applicant_name/applicant_names/rows/applicants` 字段直接拒绝。仅输出明确允许的字段，额外载荷不回显。方法备注、claim IDs、事件类型及原日期说明也不得人为嵌入身份数据；字符串内容的语义隐私需采证者核对，结构检查不能代替此项。

## 事件

除公共字段外，事件字段为 `event_type`（非空类型字符串）、`start`、`end`、`timezone`、可选 `date_text`（原公告日期表述，无身份信息）。日期使用 ISO `YYYY-MM-DD` 或 `YYYY-MM-DDTHH:MM:SS+08:00`/`Z`；未知用 null。时间区间保留 start 和 end，截止单点可令 end 为 null；不得把多天考核折成开始日。原精度、偏移与 timezone 标签原样保存，不补造时刻或时区；缺失三个时间字段的输出明确补为 null。同精度且可比较的逆向范围和非法日期被拒绝。

`reconstruct_timeline` 返回允许字段的事件列表，不改变输入。按完整 scope 首次出现顺序分组，组内依 start 排序，缺 start 事件稳定置后，end 不用于补造 start。已给 UTC 偏移的时间按真实 UTC 瞬间排序；日期或无偏移本地时间按其日历值排序。`order_basis` 为 `utc_instant/calendar_value/unknown`。不同 basis 混排只用于展示，不声称已确认精确时间先后；需要精确跨时区比较时，先从原公告核实所有时区。不同入学年、院系、专业、方向、学位和轮次不合并。

## 阶段计数

每条计数增加 `stage` 和 `count`。stage 精确枚举：

```text
announced_quota
reported_applicants
listed_shortlist
deduplicated_shortlist
confirmed_attended
excellent_campers
pre_admit
waitlist
final_admitted
```

`count` 只能是非负整数，bool、浮点、数字字符串和负值均不能参与算术。120 行入营名单只支持 `listed_shortlist=120`；去重只支持 `deduplicated_shortlist`。签到、到场官方统计等针对同一范围的真实证据才支持 `confirmed_attended`。优秀营员、拟录取、候补也不能替代到场或最终录取。

### 公示名单行数核对

先核实公告年份、单位、专业、学位、方向和轮次覆盖范围。宽口径名单不能分摊为专业或方向人数。逐页排除表头、重复页眉页脚、注释、汇总行、空行与明确非申请者行；记录排除规则和数量，无法判断的行保留为待核验而非强行计数。

`listed_shortlist` 为排除非申请者行后的原公示申请者条目数；重复申请者行若仍存在，需要注明。`deduplicated_shortlist` 仅在可解释的同一申请者识别规则下去重，不能仅凭同名判定重复；方法、原始行数和去重数量写入不含身份的备注。同一申请者跨独立轮次分别统计。明确撤回/退出行从适用的有效去重名单中排除并记录数量及公告依据；原历史公示的 listed 数和到场/最终录取数不得由此自动改写。是否到场仍需独立证据。临时查看的行身份不得写入 normalized records、测试产物或交付结果。

## 返回结构与拒算

`calculate_stage_metrics` 返回 `{"scopes": [...], "rejected": [...]}`。每组有 `scope`（七字段字典）、`scope_key`（Python tuple，JSON 序列化为数组）、`counts`（保留所有原 aggregate 记录）、`metrics` 和 `rejected`。空输入返回两个空数组。

唯一当前派生指标是 `final_admitted_per_confirmed_attended`。仅在同 scope 且双方各恰好一条合法记录、到场数大于零时，给出 numerator/denominator/value、两侧 stage、完整 scope、合并去重的 claim_ids 和 `descriptive_only=true`。不同年份绝不计算，且不推导任何未提供的阶段人数。比率可能大于 1，不能隐藏成个人概率；阶段覆盖或后续增补情况须核查。

拒算条目保存 metric、完整 scope、claim_ids 和机器原因，同时出现在该组和顶层 rejected 中：

| reason | 含义 |
| --- | --- |
| `scope_mismatch` | 有最终录取数，到场记录只在另一个精确 scope |
| `attendance_unconfirmed` | 无到场记录，本 scope 只有 listed/deduplicated 名单证据 |
| `missing_denominator` | 本 scope 无到场分母且没有名单代理证据 |
| `zero_denominator` | 同 scope 到场数为 0 |
| `invalid_count` | 非整数、bool、缺值或负数 |
| `ambiguous_stage_count` | 同 scope 同 stage 多条记录，不自动相加或选一条 |

所有重复 stage 原记录均保留并报告 ambiguous，即使数值相同。来源复核后由调用者明确选定/协调记录并保留方法与全部依据，方可另算。身份、证据引用、stage 或日期结构错误直接抛 ValueError，不输出误导性半成品。
