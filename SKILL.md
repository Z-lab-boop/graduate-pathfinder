---
name: graduate-pathfinder
description: Evidence-first Chinese graduate admission decision support for 保研 portfolios, 考研 subject gates and shortlists, application-material review, scoped previous-cycle timelines and counts, and ordinal admission outlook with uncertainty.
---

# 研途择校

先确定保研（baoyan）或考研（kaoyan），以及具体入学年份。“今年”“明年”须区分活动年、考试年与入学年；无法唯一确定时先澄清，不默默换算。混合请求先问当前正在决定哪条路径；明确要求两条路径对比时，分别建立输入与结论后对比，不合并门槛、分数或分组。

保研 v0.1：读取 [保研流程](references/baoyan-mode.md)，按 quick screen、deep portfolio、target comparison 或 refresh 执行。仅在采证时加载 [来源规则](references/source-policy.md)，评分时加载 [决策模型](references/decision-model.md)，持久化时加载 [案例契约](references/case-schema.md)，交付时加载 [报告契约](references/report-schema.md)。不要一次加载所有参考。

考研 v0.2：仅读取 [考研流程](references/kaoyan-mode.md)，按 quick screen、target comparison、deep shortlist 或 refresh 执行；科目和阈值计算时加载 [阈值契约](references/threshold-semantics.md)。不得加载保研流程来执行考研，也不得套用保研分组。只有用户明确要求跨路径对比时才分别加载两条流程。共享来源、案例、报告参考按采证、持久化、交付阶段按需加载；报告只执行当前路径对应部分。无浏览能力时据用户官方材料整理，保留缺口并停止依赖缺失事实的判断。

共享边界：以适用年份官方证据为准，目标身份到院校—院系—专业—方向—学位—轮次—入学年；缺失保持 unknown，不编造事实。区分预计与已确认推免资格，资格、适配、证据、完整度分别呈现。不得输出个人录取概率、保证录取、自动提交、代投、发送消息或接受录取。

材料与展望 v0.3：用户提供简历、成绩单、推荐信等申请材料，或询问竞争力、录取展望、往年日期、面试人数、阶段比例时，启动材料复核分支；先确定路径、当前入学年、完整目标身份及明确选择的可比历史入学年/轮次。保研按 [材料复核流程](references/baoyan-mode.md#材料复核与录取展望-v03) 执行；考研保留 v0.2 的科目、阈值和风险结论，材料部分使用 [材料规则](references/material-review.md)，不得用保研分组或 v0.3 竞争档位替代考研判定。仅需历史日期/人数的请求可交付有来源的历史表，不强制创造档案或评分。跨年度、院系、专业、学位、方向、轮次不拼接分母；历史口径不明则停在缺口。

原文件由可用 DOCX、PDF、表格或图像工具读取；无对应工具或关键页不清晰时记录 unreadable/待复核并请求可读文本或替代文件，不从文件名或 OCR 猜测核验事实。清单、材料审计、历史计算、展望及生成文本脱敏使用 `scripts/build_material_manifest.py`、`audit_materials.py`、`calculate_historical_metrics.py`、`assess_admission_outlook.py`、`redact_generated_text.py`；参数与函数按流程和参考契约调用，不编造 CLI。按需加载 [历史契约](references/historical-cycle-schema.md)，交付执行 [v0.3 报告契约](references/report-schema.md#材料复核与展望-v03-报告)。“交材料”仅指本地复核；原件不改写，材料可见不认证真实性，历史比例不代表个人概率。

请求持久化或文件交付时，使用用户指定目录，否则用当前工作目录下 `./graduate-pathfinder-cases/<case-label>/`；解析真实路径后必须在技能目录外。普通初筛可只回复聊天。案例仅本地保存，最小化并脱敏个人数据，建案例级 `.gitignore`；公开技能仓库仅合成示例。验证命令见案例契约。
