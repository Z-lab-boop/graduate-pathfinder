---
name: graduate-pathfinder
description: Evidence-first Chinese graduate admission decision support for 保研 opportunity screening, target comparison, portfolios and deadlines; 考研 requests receive evidence-only support until v0.2.
---

# 研途择校

先确定保研（baoyan）或考研（kaoyan），以及具体入学年份。“今年”“明年”须区分活动年、考试年与入学年；无法唯一确定时先澄清，不默默换算。

保研 v0.1：读取 [保研流程](references/baoyan-mode.md)，按 quick screen、deep portfolio、target comparison 或 refresh 执行。仅在采证时加载 [来源规则](references/source-policy.md)，评分时加载 [决策模型](references/decision-model.md)，持久化时加载 [案例契约](references/case-schema.md)，交付时加载 [报告契约](references/report-schema.md)。不要一次加载所有参考。

考研完整流程将在 v0.2 提供。当前只整理具体入学年份的官方目录、资格、科目和截止时间，附来源与缺口；不得套用保研门槛、评分、组合或声称已支持完整考研决策。无浏览能力时据用户给出的官方材料整理，并输出待获取证据清单。

共享边界：以适用年份官方证据为准，目标身份到院校—院系—专业—方向—学位—轮次—入学年；缺失保持 unknown，不编造事实。区分预计与已确认推免资格，资格、适配、证据、完整度分别呈现。不得输出个人录取概率、保证录取、自动提交、代投、发送消息或接受录取。

请求持久化或文件交付时，使用用户指定目录，否则用当前工作目录下 `./graduate-pathfinder-cases/<case-label>/`；解析真实路径后必须在技能目录外。普通初筛可只回复聊天。案例仅本地保存，最小化并脱敏个人数据，建案例级 `.gitignore`；公开技能仓库仅合成示例。验证命令见案例契约。
