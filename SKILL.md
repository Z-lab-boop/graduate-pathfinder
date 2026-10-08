---
name: graduate-pathfinder
description: Evidence-first Chinese graduate admission decision support for 保研 opportunities and 考研 program selection; use for source-backed candidate comparison, application portfolios, deadlines, and uncertainty-aware recommendations.
---

# 研途择校

分析前确定保研或考研路径及具体入学年份。按院校、院系、专业、学位、批次与年份记录候选项目，逐项保留来源和未知状态。

真实申请案例保存在技能目录之外；仓库仅包含合成测试。使用 `python3 scripts/validate_case.py CASE_DIR --skill-root SKILL_ROOT` 验证 `profile.json` 对象及 `candidates.json`、`evidence.json` 数组。

区分资格、适配、风险、证据可信度和完整度。缺失证据保持未知；当前规则优先使用当前年份官方来源。不得输出精确个人录取概率，不得代替用户提交申请、发送消息或接受录取。
