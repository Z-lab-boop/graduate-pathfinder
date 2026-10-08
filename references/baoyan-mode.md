# 保研 v0.1 操作流程

仅处理 summer-camp、pre-recommendation、september；regular-exam 属于后续考研版本。浏览和材料整理不授权外部提交、联系导师或改变录取状态。

## 选择流程与停止条件

| 流程 | 范围与输出 | 停止条件 |
|---|---|---|
| quick screen | 确定年份与最小档案，发现并规范目标；聊天给暂定长名单、硬门槛与缺口，通常不评分 | 用户范围已覆盖；关键问题已列出。缺关键证据即给待核验名单，不强求排名 |
| deep portfolio | 官方核验、门槛、用户评分与权重、敏感性、负荷和日程；持久化案例及报告 | 每个目标均有可追溯结论或明确缺口，组合符合用户负荷；运行验证并交付，不无限找新目标 |
| target comparison | 只比较用户指定的项目，补齐院系/方向/学位/轮次；相同证据尺度和权重 | 指定目标逐项解释、排除或待核验，不擅自扩展全国发现 |
| refresh | 读取既有案例，复核本轮官方页、归一化值、来源有效性、截止时间及用户状态 | changes.md 覆盖新增、移除、变化、新冲突、不可访问；重算受影响结论，保留用户备注 |

无浏览能力或来源无法访问时，停止依赖该事实的判断，记录 missing/stale 和获取计划；可完成不依赖它的比较。没有权重、评分尺度或足够候选时展示定性结论/insufficient_candidates，不创造输入。

## 档案采集

持久化 JSON 精确格式见 [案例契约](case-schema.md)。最小问题表：case_label、pathway=baoyan、admission_year；本科学校及专业；排名分子/分母、口径和日期；GPA 与量表；语言证据；研究兴趣；预计/确认推免资格及本校规则和最终确认日期；学位、地区、预算、职业偏好及硬约束。未知项明确写 null/unknown，不能用“前 5%”推造排名分母。

深度组合还需风险偏好、最多可准备目标数、出行限制、criterion_weights，以及各候选 dimensions 的用户尺度与依据。排名政策、现有导师联系状态与研究/项目/论文/专利/竞赛/实习贡献按用户事实记录。敏感身份和原始证件不是择校所需；可选经历若未核验，只标用户陈述。预计资格 expected 不能成为 confirmed pass；确认应有适用本校规则及正式资格证据。

## 搜索、规范与采证

1. 先查当前入学年院校研招/院系官方公告及官方系统，再查官方澄清、教师/实验室页；社区聚合仅作发现线索。搜索词包含具体年份、院校、院系、专业/方向、学位与轮次，不以学校总名录替代专业要求。
2. 按完整目标身份建 candidate_id；同院校不同院系、学位、轮次、方向分别保留。专业代码/方向不明可为 null，但不伪造已规范完整身份；院系或专业名称尚不明时保留发现笔记，暂不造合法候选记录。
3. 按 [来源规则](source-policy.md) 记录每个关键断言的 URL、标题、发布者、发布/检索时间、适用范围、tier/status、简短证据。核验网页真实内容和适用年；审计脚本不抓网页，也不验证来源标签真实性。
4. 至少覆盖 eligibility、deadline、program_availability、degree_type；其他材料、专业限制、语言要求、考核安排、费用逐项采证。没有证据也保留明确 missing 占位。冲突用同目标同年度同要求的 conflict_group，保留全部来源，不能靠层级自动消除冲突。
5. 当前年关键要求需 T1；T2 支持官方核验，T3/T4 不覆盖 T1。A–D 是自动审计置信度，不是本年适用性认证。往年规则即使今日检索也须人工标 stale/missing；门槛证据采用审计 effective_status，不能使用旧的 confirmed 绕过失效或冲突。

缺失占位的 source_url 用实际已检查的官方入口或用户提供的来源位置，publisher/title/short_evidence 如实注明“未找到该项”；不得造一个看似已抓取的公告 URL。retrieved_at 是实际检查时间。各 candidate_id 至少有证据或缺失占位，否则审计不会自动创造该候选。

## 门槛、评分与组合

先逐一核对推免资格、专业/课程、项目及学位可用性、语言、材料及截止可行性，再检查用户地区、费用、直博等硬约束；gates 要覆盖所有适用关键要求并链接依据。已官方确认的不适用项不作为门槛；缺失不是不适用。

按 [决策模型](decision-model.md) 执行：confirmed fail → excluded；关键 unknown、无关键门槛、置信度 D、权重覆盖率不足 0.70 → monitor。其他分组还需 competitive_position 与 research_fit，后者至少 60；位置 <50 为 reach、50–<80 为 core、≥80 为 safety。不得用名气推算位置；维度由用户给定尺度和理由，缺失省略不补零。评分不替代门槛。

组合在这些分组内再按用户申请负荷、期限、考核/出行冲突和研究方向分散选择；没有固定配额。说明选中与未选中的理由，避免依赖单个院校或单轮机会。评分排序不等于最终组合选择；保留 monitor/excluded，即便用户要求监控一个失败目标也不能改成 pass。safety 仅相对保守，不得保证录取。

导师适配只用官方教师/实验室方向及可归属的研究元数据；“方向相符”不代表有名额、已同意接收或录取。名额必须有当前可归属公告；联系状态仅记用户提供事实。不得基于传闻评价私人品行或自动发送联系信息。

## 时间与状态

保存截止原文、来源及原时区；明确到秒且带 offset 才写 candidate.deadline；只有日期、预计时间或未知时区时写 null，将原文和精度记在 deadline_notes，列待核验。已过期的 confirmed 截止应重新判定截止可行性门槛，不能仅凭可见公告标 pass。

日程 events 只收明确 start/end、时区及精度的考核/面试/用户准备时段。单个截止是时点，不能自动编造结束时间来生成区间；可在表格中呈现，用户明确指定提醒区间后才建日程。冲突脚本用 [start,end)，相邻不冲突；交通缓冲另按用户约束检查。未知日程不进 ICS，仍在报告警告。ICS 仅本地文件，不意味着已导入或已报名。

状态按 [案例契约](case-schema.md) 的 enum 保存；submitted、screened、assessment、offer、accepted 等进展必须有用户或官方证据，不能从报告生成、导师方向或材料齐全推断。

## 运行现有脚本

以下在技能根目录运行。CASE_DIR 是技能目录外已建立的本地案例，不能原样使用占位值。只有 validate_case.py 有命令行接口，其余模块调用函数；不得编造 CLI 参数。

```bash
python3 scripts/validate_case.py /absolute/local/case --skill-root /absolute/skill/root
```

审计可独立执行；先据结果核验门槛和更新 candidates 的 evidence_confidence，然后才排名。在 Python 中调用：

```python
from datetime import datetime, timezone
from pathlib import Path
from scripts.case_io import load_json, atomic_write_json
from scripts.audit_evidence import audit_evidence

case = Path("/absolute/local/case")
audit = audit_evidence(load_json(case / "evidence.json"), datetime.now(timezone.utc))
atomic_write_json(case / "evidence-audit.json", audit)
```

人工检查审计 errors、候选缺失、适用年份、冲突与有效门槛后，在同一 Python 会话中继续，使用已保存的用户权重和评分运行分析。此代码不会替代上述人工核验：

```python
from scripts.rank_candidates import rank_candidates
from scripts.sensitivity_analysis import analyze_sensitivity
from scripts.detect_schedule_conflicts import detect_conflicts
from scripts.generate_calendar import render_ics

profile = load_json(case / "profile.json")
candidates = load_json(case / "candidates.json")
weights = profile["preferences"]["criterion_weights"]
ranked = rank_candidates(candidates, weights)
atomic_write_json(case / "ranked-candidates.json", ranked)
atomic_write_json(case / "sensitivity.json", analyze_sensitivity(candidates, weights, delta=0.10))
# 仅用户要求日程且 events.json 内时间已确认时执行：
events = load_json(case / "events.json")
atomic_write_json(case / "schedule-conflicts.json", detect_conflicts(events))
with (case / "deadlines.ics").open("wb") as stream:
    stream.write(render_ics(events, "保研申请日程").encode("utf-8"))
```

首次写输出前检查同名文件，保留旧版或用户修改；atomic_write_json 提供单文件原子更新，不是整个案例事务或备份。刷新只更新已确认变化，保留用户备注和旧证据历史，重新验证。

按 [报告契约](report-schema.md) 生成 report.md 和 candidate-matrix.csv；解释敏感性 stable/fragile/insufficient_candidates、实际权重及网格阈值局限。完成标准是可追溯交付或具体缺口，不是录取结论。
