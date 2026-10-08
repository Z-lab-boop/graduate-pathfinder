# 研究基础与复用状态

本文档记录 Graduate Pathfinder 的开源调研面，方便检查“参考了什么”和“实际复用了什么”。检索日期为 **2026-10-09**；本轮查看了各仓库的公开首页、README 或仓库结构。这不是文件级代码或许可审计，也不是对其数据准确性、完整性或实时性的背书。

## 状态定义

- `idea-only`：仅提炼抽象机制或产品思路；本仓库未复制其代码、模板、schema、实质性表达或数据。
- `data-not-redistributed`：项目提供了数据组织、来源分级或更新机制的调研样本；本仓库不再分发其数据。
- `code-adapted-with-license`：仅在已完成文件级许可核验、保留所需归属且有对应记录时使用。初始发布中无此类条目。

## 保研机会发现与日期

| 项目 | 通用机制启发 | 复用状态 |
| --- | --- | --- |
| [CS-BAOYAN/BoardCaster](https://github.com/CS-BAOYAN/BoardCaster) | 用结构化记录、Issue/PR 和原始链接协作维护机会；社区线索与官方确认应分层 | `data-not-redistributed` |
| [CS-BAOYAN/CS-BAOYAN-DDL](https://github.com/CS-BAOYAN/CS-BAOYAN-DDL) | 把机会数据映射为截止日期列表/日历，并暴露紧迫度与数据年份 | `data-not-redistributed` |
| [CS-BAOYAN/CSLabInfo](https://github.com/CS-BAOYAN/CSLabInfo) | 实验室和导师招生广告可作发现线索，不能替代招生单位对名额、资格和轮次的官方确认 | `data-not-redistributed` |
| [BairlyEmei/baoyan-archive](https://github.com/BairlyEmei/baoyan-archive) | 按项目与时间线组织历届档案，配合链接规则和版本化质量检查 | `data-not-redistributed` |

Graduate Pathfinder 只把这些仓库当作发现入口或工作流样本。当前资格、截止时间、材料和考核安排仍需按入学年份核对对应招生单位的官方来源。

## 本地申请工作流

| 项目 | 通用机制启发 | 复用状态 |
| --- | --- | --- |
| [BlairCode/baoyan_workbench](https://github.com/BlairCode/baoyan_workbench) | 本地管理材料索引、目标、状态、待办与备份，将申请进展与文件分类联系 | `idea-only` |
| [Sa63R/baoyan-prep](https://github.com/Sa63R/baoyan-prep) | 将有来源资料、通用准备材料与 AI 生成内容的信任边界分开 | `idea-only` |
| [granitehq/college-tools](https://github.com/granitehq/college-tools) | 以用户可见的指标、核对项和进展表格组织多目标选择 | `idea-only` |
| [satyam-thakur/profscout](https://github.com/satyam-thakur/profscout) | 研究方向适配、来源外链与本地/客户端隐私可以分开设计；自动联系不属于本 skill 范围 | `data-not-redistributed` |

## 考研目录、口径与快照

| 项目 | 通用机制启发 | 复用状态 |
| --- | --- | --- |
| [Laz8Noy/kaoyan408-share](https://github.com/Laz8Noy/kaoyan408-share) | 将院校数据、多源核对、录取分数统计与学习资源分区，并保留数据征集规则 | `data-not-redistributed` |
| [XieShawn-XXL/kaoyan-recommendation-platform](https://github.com/XieShawn-XXL/kaoyan-recommendation-platform) | 官方快照、科目精确匹配、缺失不估算、口径分层、快照哈希和发布阻断 | `data-not-redistributed` |
| [xx025/yanx](https://github.com/xx025/yanx) | 将招生目录下载成机器可读快照，但快照仍需绑定年份和检索时间 | `data-not-redistributed` |
| [DaoMingze/yztool](https://github.com/DaoMingze/yztool) | 按招生流程区分目录、初试、复试、调剂和拟录取，并输出可复查的结构化数据 | `data-not-redistributed` |

这些仓库的任何快照都没有被打包到 Graduate Pathfinder。对研招网或招生单位页面的访问必须遵守来源条款、机器人规则和访问限制。

## 证据治理与数据边界

| 项目 | 通用机制启发 | 复用状态 |
| --- | --- | --- |
| [vibewatch/UniRank](https://github.com/vibewatch/UniRank) | 为每个观测保留来源、范围、时间、抽取方法、置信和冲突组，受限数据与开放数据分层存储 | `data-not-redistributed` |
| [lghui12138/gaokao-zhiyuan](https://github.com/lghui12138/gaokao-zhiyuan) | 官方来源快照、OCR 审计、口径标签、累计数连续性校验与不可混用的人群分层 | `data-not-redistributed` |

这两个项目仅用于调研通用的数据治理思路；高考、排名数据或其中的任何数据集不是本项目的研究生招生事实来源。

## 多准则决策、敏感性与稳定性

| 项目 | 通用机制启发 | 复用状态 |
| --- | --- | --- |
| [Valdecy/pyDecision](https://github.com/Valdecy/pyDecision) | 多准则决策方法可以系统比较备选方案，但方法输出不能被解读为招生概率 | `idea-only` |
| [dabrze/mcda-vista](https://github.com/dabrze/mcda-vista) | 扫描准则空间来可视化排序方法的区域、边界和不稳定性 | `idea-only` |
| [miguepoloc/mcda-tools](https://github.com/miguepoloc/mcda-tools) | 显式准则方向、容差、多方法对比和独立验证可提高决策计算的可审计性 | `idea-only` |
| [brianwendr/decision-analytics-toolkit](https://github.com/brianwendr/decision-analytics-toolkit) | 权重敏感性、排名稳定性、方案增删导致的排名反转，以及可复现的决策模型说明 | `idea-only` |

Graduate Pathfinder 的透明加权基线、敏感性情景和稳定性提示均为独立实现。它们只服务于当前候选集与用户偏好下的比较，不是录取模型。

## 初始发布的复用结论

- 没有第三方代码、schema、模板或实质性表达被标记为 `code-adapted-with-license`。
- 没有上述仓库的招生数据、排名数据、联系人数据或快照被再分发。
- 仓库内的代码、契约和测试为针对本项目边界的独立实现；公开 fixtures 只含虚构机构、保留域名和合成个人信息。
- 如后续引入第三方文件，须先记录具体文件、版本/提交、许可条款、归属位置和数据条款，再将本文档的对应状态更改为 `code-adapted-with-license`。
