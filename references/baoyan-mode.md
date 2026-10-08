# 保研操作流程（v0.1 组合 / v0.3 材料与展望）

仅处理 summer-camp、pre-recommendation、september；regular-exam 属于后续考研版本。浏览和材料整理不授权外部提交、联系导师或改变录取状态。

## 选择流程与停止条件

| 流程 | 范围与输出 | 停止条件 |
|---|---|---|
| quick screen | 确定年份与最小档案，发现并规范目标；聊天给暂定长名单、硬门槛与缺口，通常不评分 | 用户范围已覆盖；关键问题已列出。缺关键证据即给待核验名单，不强求排名 |
| deep portfolio | 官方核验、门槛、用户评分与权重、敏感性、负荷和日程；持久化案例及报告 | 每个目标均有可追溯结论或明确缺口，组合符合用户负荷；运行验证并交付，不无限找新目标 |
| target comparison | 只比较用户指定的项目，补齐院系/方向/学位/轮次；相同证据尺度和权重 | 指定目标逐项解释、排除或待核验，不擅自扩展全国发现 |
| refresh | 读取既有案例，复核本轮官方页、归一化值、来源有效性、截止时间及用户状态 | changes.md 覆盖新增、移除、变化、新冲突、不可访问；重算受影响结论，保留用户备注 |
| material review / admission outlook | 本地材料、目标要求、明确历史轮次、五项独立展望；输出 v0.3 报告 | 逐项目材料状态与缺口可追溯，历史比例算出或明确拒算；敏感文本脱敏后交付，不等待或推断录取 |

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

以下在技能根目录运行。CASE_DIR 是技能目录外已建立的本地案例，不能原样使用占位值。validate_case.py 和 v0.3 的 build_material_manifest.py 有命令行接口；其余模块调用函数，不得编造 CLI 参数。

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

## 材料复核与录取展望 v0.3

用户给材料、问竞争力/录取展望、去年日期/人数/阶段比率时进入此分支。确定当前入学年与目标 candidate_id，核实院校、院系、专业代码、学位、方向及轮次，并明确历史 cohort 的入学年和轮次；用于当前展望的历史入学年必须严格早于当前目标入学年，当前年或未来年不能冒充历史样本。`candidate.round` 对应历史 `admission_round`，必须显式归一化，不能把拼写差异当作通配符。往年日期不覆盖本年截止。目标或范围不清时先完成不依赖它的材料清单，停止目标门槛与比例判断。

1. 按用户选定路径原位建立 `materials-manifest.json`，不复制原件，不写回来源。CLI：`python3 scripts/build_material_manifest.py --file /absolute/selected/material --case-root /absolute/local/case`；多文件重复 `--file`。案例路径必须在技能目录外，检查同名输出并保留旧版。清单中的真实绝对路径和哈希仅作本地溯源，不放公开报告。
2. 读取 [材料规则](material-review.md)，由可用文档/PDF/表格/图像工具观察实际内容，标注 document_class、extraction_state、页码/位置及六类 applicant claim states。简历 GPA 仍是 user_asserted；成绩单观察可为 document_verified，但不认证真伪。签名/日期用 document scope。OCR 不确定不升级 verified。字段尺度不一致先区别口径；同口径矛盾保留全部 claim IDs/值，不选有利值。无读取能力或关键页模糊就保留未读状态并请求替代文本/清晰文件。
3. 将本年官方目标要求保存为本地 `material-requirements.json`，每项绑定 requirement_id、target_id、necessity、typed conditions、source_claim_ids 和选定 document_ids。推荐信需签名/日期时逐封检查；草稿不等于完成。官方证据 value 必须精确含该要求的 policy binding，完整 `audit_evidence` 报告需支持该 candidate 和本年；不能用 ID 或 A 标签代替核验。调用 `audit_materials(manifest, claims, requirements)`，缺签名、日期、可读性或矛盾均列补证动作，停止完成声明。
4. 读取 [历史契约](historical-cycle-schema.md)，归一化事件、计数与来源，公开名单只保留总量和排除/去重方法。所有计数均有七字段 scope、claim IDs、来源 URL、实际检索日、证据层级；listed/deduplicated 不升级 attended。调用 `reconstruct_timeline(events)` 和 `calculate_stage_metrics(counts)`；各 scope 原计数、拒算理由和两侧来源均保留。跨范围的 20/80 不计算；仅同 scope 的 confirmed_attended 支持最终录取/到场比率。无人数证据仍可交付日期及缺口。
5. 只有已有明确竞争尺度/理由、权重、完整门槛和官方历史支持时才作数值展望。先以审计后的有效证据更新门槛，运行 `evaluate_gates` 和 `score_candidate`，再调用 `assess_admission_outlook(payload)`。payload 含当前 candidate_id/admission_year、选定历史 `target_scope` 七字段、eligibility_result、material_audit、candidate_scoring、historical_metrics、fit_result（score/reasons）及完整 evidence_audit。历史 scope 的入学年必须严格早于当前入学年；缺少 fit_result 或 score 时保留 `score: null` 与缺失原因，不能补成 0，真实的数值 0 仍有效。竞争档位仅使用显式 competitive_position 的 80/60/40 序数规则，不用 weighted_score、校名或历史比率推造输入；无可比历史/关键矛盾/本年要求不可用时为 evidence_insufficient。独立呈现资格、材料、竞争档位、适配与置信度，既有 v0.1 分组仍依其原契约，不自动互换。
6. 按 [v0.3 报告契约](report-schema.md#材料复核与展望-v03-报告) 保存最小化本地归一化数据与五份交付文件。生成 Markdown/展示文本后先调用 `redact_text(text)` 再保存，findings 仅保留类型/次数/复核标志；不留未脱敏报告副本。手动检查姓名、住址、图片、路径和组合身份以及误脱敏；此检查未完成须明示 privacy review pending，不能宣称匿名化完成。合成测试不证明真实材料或招生准确性。

这些接口除清单 CLI 外均为纯函数，不联网、不自动解析文档、不提交。可在既有 Python 分析会话中调用并使用 `atomic_write_json` 保存审计、历史与展望结果；它不创建父目录，也不提供案例备份。保存前建目录并保护既有用户内容。历史全范围拒算结果保存在 historical-cycle.json；outlook 的 historical_context 仅含选定 scope 的重新核算结果，两者不能互相替代。缺必要输入时交付具体缺口和未执行理由，不创造评分/合成人数来完成报告。
