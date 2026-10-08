# 考研 v0.2 操作流程

仅执行 pathway=kaoyan、round=regular-exam；保研门槛与 reach/core/safety 组合不适用。科目、阈值、分数计算遵循 [阈值契约](threshold-semantics.md)，采证遵循 [来源规则](source-policy.md)，基础 JSON 与隐私边界遵循 [案例契约](case-schema.md)，交付遵循 [报告契约的考研部分](report-schema.md#考研-v02-报告)。本流程补充基础案例契约中的考研 v0.2 扩展；基础校验成功不代表扩展、事实或来源真实性已校验。v0.3 材料审阅、外部提交等功能不在本流程内。

## 流程、输入与停止条件

| 流程 | 范围与输出 | 停止条件 |
|---|---|---|
| quick screen | 聊天给当前项目、科目门、适用线层级、暂定名单及缺口；证据不足时不强行定风险带 | 用户范围已覆盖，关键未知与获取计划已列明 |
| target comparison | 仅比较用户指定目标；按同一分数情景、证据口径解释适配与风险 | 每个指定目标有可追溯判断或明确缺口，不扩大全国发现 |
| deep shortlist | 官方核验、科目门、分数区间、风险带、偏好敏感性、shortlist 与报告 | 每个目标均有结果或 monitor/excluded 理由，必要验证完成；单主目标条件不足时保留 decision_set |
| refresh | 复查既有案例的本年目录、科目、阈值来源、复试规则、费用及用户事实 | changes.md 覆盖新增/移除/变化/新冲突/不可访问，受影响分析重算，保留旧证据与用户备注 |

先收集：明确入学年（另记考试年，不能默默换算）；专业类别/专业族及接受的具体专业；academic-master 或 professional-master；完整有序科目代码组合；用户预计总分与各科区间、情景年份/阈值 scope/人群；全日制/非全日制（study_mode 为 full-time/part-time）、专项计划（special_plan 为明确计划标识，无专项可明示 ordinary）；地区、费用口径与预算、职业/研究偏好及硬约束；是否愿意换科目（preferences.willing_to_switch_subjects 必须为布尔）。未知保持 null/unknown，不由代理预测分数。

深度分析还需用户给定 fit_score（0–100）的尺度、理由、completeness_basis（决策字段分母与已知计数）、historical_volatility 与 retest_risk 的 low/medium/high 判断及依据。缺历史数据、复试规则或无法给出有依据的类别时保持 unknown，不把未知写成 low。偏好权重/维度未提供则不运行敏感性，shortlist 保留待用户决策。风险偏好、备考换科成本、位置与学费等约束均给出用户事实和官方规则各自依据。

## 官方发现与证据

1. 从目标入学年院校研招官网、院系目录及官方报名系统发现专业；搜索包含具体年份、院系、专业代码、方向、学位、学习方式。社区只作发现线索，不以旧名录证明本年招生。
2. 身份规范到 institution/unit/program_code/program_name/research_track/degree_type/round/admission_year/pathway；学习方式、地区、类别、计划/人群另明确。不同方向、学位、学习方式或计划保持独立候选，不能按校名合并。身份未知保留缺口。
3. 本年逐项确认 program_availability、degree_type、eligibility、deadline 以及科目、学习方式、计划限制、费用和复试要求。每个证据保留完整 v0.1 字段及 applicable_admission_year；官方来源标签、网页内容、年份和目标归属由采证者核实。未找到项在实际检查入口留 missing 占位；无法访问不等于撤招。
4. current_catalog 必须为本年当前官方、field=program_availability、value 为字面 true 的完整证据记录，candidate_id 与目标一致。把该记录原样放入 evidence.json；审计 claims 中同 claim_id 必须存在、record 内容和值类型与 current_catalog 完全一致，valid=true、effective_status=confirmed、无 stale/conflict_groups。缺失、修改后未重审、争议或同目标同年官方 false 均保留 monitor 理由，不能以另一个目录记录替代绑定。
5. 历史逐年收集原官方阈值、复试办法和已录取分数统计，记录样本口径、年份、scope、人群/statistic、科目及全部身份限定。不同年、层级与统计量分开；录取分布仅描述，不转换成线或未来门槛。未来线未公布时保持 insufficient_evidence。历史波动与复试风险说明依据及缺失，不能凭声誉生成。

current official 的计算口径为结构有效、T1/T2、confirmed、适用年份一致、在 profile.audit_at 日龄 0..365 天、发布日不晚于审计日且无过期/冲突；audit_at 必须带时区，明确保存以便复算。全部关键字段仍需人工核对适用入学年。A–D 仅审计置信度，不验证官方发布者或招生事实。

## 科目、阈值与审计绑定

profile/candidate.subject_combination 均为 `{codes: [...], evidence: [...]}`；完整有序代码按 NFKC 与首尾空白归一化，保留前导零；证据 value 支持相同完整序列。无证据/争议为 unknown；确认不匹配且未明确愿意换科为 fail。愿意换科仅允许确认差异进入 pass，仍需报告 switch_required/differences；情景必须显式提供目标 subject_codes，不能沿用旧组合分数或声称已完成换科。

将双方科目证据及每条 threshold.evidence 原样加入 evidence.json 并统一审计，不能只审计四个基础关键字段。直接决策调用科目/分数函数必须传完整 audit 第三参数；每个消费 claim_id 必须存在，审计 record 与嵌入记录递归内容及类型一致，valid=true、effective_status=confirmed、stale=false、conflict_groups=[]。审计失效不能被 raw status=confirmed 覆盖；科目 unknown、分数 insufficient_evidence 会保持 monitor，输出保留原记录、绑定理由和 source IDs。省略第三参数只为兼容直接形状/算术调用，不构成决策证据。

thresholds 每条保留 year/scope/total/source_ref/subject_codes、population、已公布 subject_minimums、身份限定和 evidence；admitted_distribution 另有 statistic。每年的完整 subject_codes 必须由该年的阈值证据支持，不能从当前组合反推。evidence 的 claim_id=source_ref、candidate_id 对齐、applicable_admission_year=threshold.year，value 完整支持原阈值事实及限定，不能丢弃单科、人群、地区或类别。institution/unit/program/direction/admitted_distribution 的必需身份见阈值契约；所有已填写限定都须与目标一致。national 必须有非空 area/category，目标也必须明确且完全一致，population 文本不能替代这两项。国家线不能当作专业线；专业代码不会提升 scope。

适用限定还包含 study_mode/special_plan：candidate、threshold、source payload 中的限制递归内容和值类型须一致；来源单独写明学习方式或专项时，不得忽略。支持字段清单和备注边界见阈值契约；非 null 的不支持限定（含任意 applicability 容器）拒绝，返回具体缺口，不靠人群文字隐式解释。

score_scenario 为用户范围：year/scope/population/total=[low,high]/subjects={code:[low,high]}，描述统计另带 statistic，必要时显式 subject_codes。只比较同年、同 scope/人群/统计口径、同身份与完整科目的可用记录；每条公布最低分的单科均需用户范围。margin=[low-line,high-line]；所有下界严格高于线为 above，任一完整区间上界低于线为 below，其他为 overlaps（含等于）；缺项或兼容记录矛盾为 insufficient_evidence。comparisons 与 excluded_thresholds 均完整保留，不能只挑最低线。

assess_kaoyan_candidate 第三参数必须传 audit_evidence 的完整输出 `{claims,candidate_summary,conflicts,errors}`，禁止只传 candidate_summary 或手写置信度。每个关键字段 eligibility/deadline/program_availability/degree_type 需同目标同入学年、非 null、当前官方且 effective_status=confirmed 的原始 claim，摘要也须无缺失/争议/无效/过期/二手依赖。summary-only 会以 current_critical_source_provenance_missing 留 monitor。先检查审计 errors、claims 和引用，再按有效证据重核 gates；原 confirmed 不能绕过审计失效。保留完整返回值。

考研 gates 的来源扩展为 `evidence: [完整原始记录, ...]`，可另写 `source_refs: [claim_id, ...]`；既有 candidate.gate_bases[gate_id] 也作为必需解析的引用。每条原始证据必须属于该候选、适用本入学年、满足 current official，并与完整审计递归绑定；每一个引用都须由该 gate 的原始证据覆盖。缺原记录、额外未覆盖引用、来源变化、无效/过期/冲突均将原 pass/fail 降为 unknown。gate_evaluation.audit_bindings 保留声明门、所有引用和拒绝理由；即使失效门原来非 critical，也须 monitor，不能沿用旧 fail 排除。可用审计支持的 confirmed fail 仍 excluded；pass/fail 的事实推导由采证者说明，脚本只验证声明状态和依据可用性，不代替人工资格解释。

## 风险带与 shortlist

先处理 confirmed 科目 fail 或 gates fail → excluded。其余任何关键未知、目录/审计未绑定、置信度 D、data_completeness 未达 0.70（或非法）、fit_score 未达 60（或未知/非法）、波动/复试风险 unknown、无兼容非描述性比较 → monitor。有效置信度取审计与候选声明中较差者，缺任一有效声明按 D。

通过上述条件后：分数 below 或波动/复试任一 high → reach；分数 above、每条 total_margin 下界 ≥20、fit≥60、置信度 A/B、波动 low、复试风险非 high → conservative；其余有效 above/overlaps 为 match。20 分、60 分与 0.70 是显式决策规则，未经录取结果校准。风险带只用于当前情景决策，不是个人录取概率，conservative 不保证录取，也不表示复试资格已经确认。

build_kaoyan_shortlist 输入为 candidate_id → 完整 assessment 输出，输出固定键 `primary,decision_set,requires_user_decision,alternatives,monitor,excluded,reasons`。仅 match/conservative 可成为主选择，按用户 fit_score 排序；候选 ID 只用于确定展示顺序，不能裁定同分赢家。所有最高适配并列目标的 winner_set 合并后与 eligible 目标相交；有 fragile 时保留并列目标及相关赢家为 decision_set（不足两项则保留全部 eligible），同分也须用户决策。只有唯一最高适配、stable、winner_set=[该目标] 且若存在 baseline_order 则其首项为该目标，才给 primary。缺失/不足敏感性保留全部 eligible 为 decision_set。无 eligible 时 primary=null、decision_set=[]，说明 no_eligible_match_or_conservative_target；reach 可作 alternatives，monitor/excluded 单列且不升级。

## 精确运行方式

以下在技能根目录运行，替换绝对路径；仅 validate_case.py 有 CLI，其余调用函数。只有用户要求文件交付才建技能目录外案例；先检查同名输出并保留旧版或用户修改，atomic_write_json 不提供案例事务或备份。

```bash
python3 scripts/validate_case.py /absolute/local/case --skill-root /absolute/skill/root
python3 - <<'PY'
from datetime import datetime
from pathlib import Path
from scripts.case_io import load_json, atomic_write_json
from scripts.audit_evidence import audit_evidence
case = Path('/absolute/local/case')
profile = load_json(case / 'profile.json')
audit = audit_evidence(load_json(case / 'evidence.json'),
                       datetime.fromisoformat(profile['audit_at'].replace('Z', '+00:00')))
atomic_write_json(case / 'evidence-audit.json', audit)
PY
```

检查并修正证据、门槛与完整度依据后重新验证/审计。共享敏感性调用 v0.1 排名器，要求其合法 weights/dimensions、有效 gates、足够权重覆盖及 competitive_position/research_fit 的用户尺度和依据；不为运行脚本虚构这些输入。内部 portfolio_group 仅影响共享排名器的可排序集合，不作为考研风险带或资格。报告说明共享分析实际参与/排除的候选；其 weighted_score 与考研 fit_score 是不同输出，最高适配目标未满足 shortlist 条件时保留决策集合。缺权重或尺度省略 sensitivity；脚本不会自动预测招生变化，事实变化或用户改分数须另建情景复算。

```bash
python3 - <<'PY'
from pathlib import Path
from scripts.case_io import load_json, atomic_write_json
from scripts.assess_kaoyan import assess_kaoyan_candidate, build_kaoyan_shortlist
from scripts.sensitivity_analysis import analyze_sensitivity
case = Path('/absolute/local/case')
profile = load_json(case / 'profile.json')
candidates = load_json(case / 'candidates.json')
audit = load_json(case / 'evidence-audit.json')  # 完整审计，不能切出摘要
for candidate in candidates:
    candidate.pop('sensitivity', None)  # 不沿用未核验旧分析
# 仅在用户提供权重和各维度尺度/依据、门槛与证据已复核时执行：
# sensitivity = analyze_sensitivity(candidates, profile['preferences']['criterion_weights'], delta=0.10)
# atomic_write_json(case / 'sensitivity.json', sensitivity)
# for candidate in candidates:
#     candidate['sensitivity'] = sensitivity
results = {c['candidate_id']: assess_kaoyan_candidate(profile, c, audit) for c in candidates}
atomic_write_json(case / 'kaoyan-assessments.json', results)
atomic_write_json(case / 'kaoyan-shortlist.json', build_kaoyan_shortlist(results))
PY
```

敏感性必须与本轮输入/权重/候选集合绑定，不复用未核验的旧 candidate.sensitivity。仅用户要求日程且 events 起止/时区已确认时运行以下共享函数；不明时间列待核验，生成 ICS 仅代表本地文件。

```bash
python3 - <<'PY'
from pathlib import Path
from scripts.case_io import load_json, atomic_write_json
from scripts.detect_schedule_conflicts import detect_conflicts
from scripts.generate_calendar import render_ics
case = Path('/absolute/local/case')
events = load_json(case / 'events.json')
atomic_write_json(case / 'schedule-conflicts.json', detect_conflicts(events))
with (case / 'deadlines.ics').open('wb') as stream:
    stream.write(render_ics(events, '考研日程').encode('utf-8'))
PY
```

日期精度、状态更新、隐私与路径规则沿用基础案例契约，不自动报名、发送消息、联系导师或接受录取。

缺当前目录/科目、历史适用性或复试证据时停止依赖它的分组，交付具体官方待查项；可完成其他已知比较。报告与 CSV 取脚本完整结果及原来源，保留 excluded_thresholds/reasons。完成表示分析或缺口可追溯，不表示真实录取或已完成外部操作。
