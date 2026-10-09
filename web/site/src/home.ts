import type { Language } from "./i18n.js";

const en = {
  "home.folio": "Field guide / 01",
  "home.hero.note": "A clearer decision begins with a traceable claim.",
  "home.concept": "Concept artwork",
  "home.hero.caption": "An imagined admissions archive. Generated imagery; no real documents or institution.",
  "home.hero.alt": "Concept artwork: blank application folders, translucent timeline strips and plain brass tools on a dark archival desk.",
  "home.workflow.heading": "From a profile to a considered outlook.",
  "home.journey.intro": "Five stages. One evidence trail. Follow what is known, what is missing, and what needs another look.",
  "home.journey.label": "Application journey",
  "home.profile": "Profile", "home.materials": "Materials", "home.targets": "Targets", "home.history": "History", "home.outlook": "Outlook",
  "home.profile.question": "Start with the right context.",
  "home.profile.body": "Name the intake year, applicant route and academic background. A requirement only matters when it applies to your case.",
  "home.profile.note": "Context before comparison",
  "home.materials.question": "Read beyond the checklist.",
  "home.materials.body": "Review resumes, transcripts and recommendation drafts. Keep extraction uncertainty, missing signatures and target-specific gaps visible.",
  "home.materials.note": "A file exists ≠ a material is ready",
  "home.targets.question": "Compare claims, not reputations.",
  "home.targets.body": "Separate eligibility, fit, material readiness and evidence confidence for each target. Keep every requirement connected to its source.",
  "home.targets.note": "One target, several independent dimensions",
  "home.history.question": "Give every count a scope.",
  "home.history.body": "Read previous-cycle interview timelines and stage counts with their year, route, numerator and denominator. Incompatible scopes stay unresolved.",
  "home.history.note": "Past cohort ratios are not personal probabilities",
  "home.outlook.question": "Make uncertainty part of the decision.",
  "home.outlook.body": "Bring the evidence together into an ordinal outlook. Surface the next review step alongside missing and conflicting information.",
  "home.outlook.note": "Decision support, with no admission guarantee",
  "home.legend.heading": "Read the evidence state",
  "home.confirmed": "Confirmed", "home.missing": "Missing", "home.conflicted": "Conflicted", "home.review": "Review required",
  "home.legend.body": "Status follows the claim. Unknowns remain visible until evidence resolves them.",
  "home.preview.label": "Synthetic product walkthrough",
  "home.preview.heading": "See how a claim travels.",
  "home.preview.intro": "A fictional example of the review flow, rendered as product UI. All records below are invented.",
  "home.preview.case": "FICTIONAL CASE / MATERIAL REVIEW",
  "home.preview.source.label": "Source claim",
  "home.preview.source": "Target requires a signed recommendation.",
  "home.preview.source.note": "Fictional requirement · target-specific",
  "home.preview.document.label": "Material check",
  "home.preview.document": "Recommendation draft",
  "home.preview.document.note": "Signature absent in the fictional draft.",
  "home.preview.action.label": "Next review step",
  "home.preview.action": "Confirm signature requirements.",
  "home.preview.action.note": "Guidance only · applicant reviews locally",
  "home.preview.boundary": "A visible gap stays open. It is not silently converted into readiness.",
  "home.art.heading": "Materials in context. Routes in perspective.",
  "home.art.folio": "Field notes",
  "home.art.intro": "The archive is a visual metaphor. Your actual materials and decisions stay in your local workflow.",
  "home.materials.caption": "Anonymous paper layers and a blank envelope. Generated concept; not applicant evidence.",
  "home.materials.alt": "Concept artwork: blank envelope, anonymous document layers, geometric checklist and teal and cinnabar tabs.",
  "home.campus.caption": "Light traces possible routes through an imagined campus. Generated concept; not a real university.",
  "home.campus.alt": "Concept artwork: a fictional architectural corridor with branching bands of light, no people or institutional signs.",
  "home.privacy.heading": "Your materials stay with you.",
  "home.privacy.strip": "No uploads · no admission guarantees",
  "home.privacy.body": "Use the Skill in your local Codex workspace. This public site explains the workflow using fictional examples; it accepts no applicant documents and has no tracking.",
  "home.privacy.link": "Read the evidence & privacy boundaries"
} as const;

const zh = {
  "home.folio": "案头指南 / 01",
  "home.hero.note": "清晰的判断，始于可追溯的证据。",
  "home.concept": "概念艺术图",
  "home.hero.caption": "想象中的招生档案桌。生成图像，不含真实文件或院校。",
  "home.hero.alt": "概念艺术图：深色档案桌上的空白申请文件夹、半透明时间线纸条和无字黄铜工具。",
  "home.workflow.heading": "从背景出发，形成审慎的展望。",
  "home.journey.intro": "五个阶段，一条证据链。沿途看清已知、缺失，以及需要再次复核的内容。",
  "home.journey.label": "申请路径",
  "home.profile": "背景", "home.materials": "材料", "home.targets": "目标", "home.history": "历史", "home.outlook": "展望",
  "home.profile.question": "先明确适用的背景。",
  "home.profile.body": "明确入学年份、申请路径和学业背景。只有适用于你的案例，招生要求才有比较意义。",
  "home.profile.note": "先核对背景，再比较目标",
  "home.materials.question": "复核不止于清单。",
  "home.materials.body": "复核简历、成绩单与推荐信草稿。清晰保留提取不确定性、缺失签字和各目标的具体材料缺口。",
  "home.materials.note": "文件存在 ≠ 材料就绪",
  "home.targets.question": "比较有来源的判断。",
  "home.targets.body": "针对每个目标，分别呈现资格、适配、材料就绪度与证据信心，让每项要求都连接到其来源。",
  "home.targets.note": "一个目标，多个独立维度",
  "home.history.question": "让每个人数都有口径。",
  "home.history.body": "查看上年度复试时间线与阶段人数时，同时核对年份、路径、分子和分母。不一致的口径保留未解决状态。",
  "home.history.note": "历史群体比率不是个人录取概率",
  "home.outlook.question": "将不确定性纳入判断。",
  "home.outlook.body": "汇总证据，形成序数展望，同时呈现下一步复核事项、缺失信息与冲突。",
  "home.outlook.note": "决策支持，不保证录取",
  "home.legend.heading": "读懂证据状态",
  "home.confirmed": "已确认", "home.missing": "缺失", "home.conflicted": "有冲突", "home.review": "需复核",
  "home.legend.body": "状态对应具体判断。在证据解决问题之前，未知项始终可见。",
  "home.preview.label": "合成产品流程演示",
  "home.preview.heading": "看一项判断如何传递。",
  "home.preview.intro": "以产品界面呈现的虚构复核流程。下列记录全部为虚构示例。",
  "home.preview.case": "虚构案例 / 材料复核",
  "home.preview.source.label": "来源判断",
  "home.preview.source": "目标要求提交已签字推荐信。",
  "home.preview.source.note": "虚构要求 · 适用于特定目标",
  "home.preview.document.label": "材料检查",
  "home.preview.document": "推荐信草稿",
  "home.preview.document.note": "虚构草稿中缺少签字。",
  "home.preview.action.label": "下一步复核",
  "home.preview.action": "确认签字要求。",
  "home.preview.action.note": "仅作指导 · 申请者在本地复核",
  "home.preview.boundary": "可见缺口保留未解决状态，不会被悄然视为材料就绪。",
  "home.art.heading": "材料有背景，路径有参照。",
  "home.art.folio": "案头札记",
  "home.art.intro": "档案意象是一种视觉比喻。真实材料与申请决策留在你的本地工作流程中。",
  "home.materials.caption": "匿名纸张与空白信封。生成概念图，不是申请者证据。",
  "home.materials.alt": "概念艺术图：空白信封、匿名文件、几何清单与青绿、朱砂色标签。",
  "home.campus.caption": "光线穿过想象校园，勾勒多条路径。生成概念图，不是真实大学。",
  "home.campus.alt": "概念艺术图：虚构建筑长廊中分岔的光带，无人物或院校标识。",
  "home.privacy.heading": "你的材料，由你保管。",
  "home.privacy.strip": "不接受上传 · 不保证录取",
  "home.privacy.body": "在本地 Codex 工作区中使用 Skill。本网站通过虚构示例解释流程，不接收申请文件，也不进行追踪。",
  "home.privacy.link": "阅读证据与隐私边界"
} satisfies Record<keyof typeof en, string>;

export const homeCopy: Record<Language, Record<string, string>> = { en, "zh-CN": zh };

export function initHome(): void {
  const journey = document.querySelector<HTMLElement>("[data-journey]");
  if (!journey || journey.dataset.initialized) return;
  journey.dataset.initialized = "true";
  const links = Array.from(journey.querySelectorAll<HTMLAnchorElement>("[data-stage-link]"));
  const stages = Array.from(document.querySelectorAll<HTMLElement>("[data-stage]"));
  const ids = new Set(stages.map((stage) => stage.id));
  let current = ids.has(location.hash.slice(1)) ? location.hash.slice(1) : "profile";
  const select = (id: string, history: "push" | "replace" | "none" = "none", scroll = false) => {
    if (!ids.has(id)) return;
    current = id;
    links.forEach((link) => {
      if (link.hash === `#${id}`) link.setAttribute("aria-current", "step");
      else link.removeAttribute("aria-current");
    });
    stages.forEach((stage) => { stage.dataset.active = String(stage.id === id); });
    if (history !== "none" && location.hash !== `#${id}`) {
      window.history[history === "push" ? "pushState" : "replaceState"](null, "", `#${id}`);
    }
    if (scroll) document.getElementById(id)?.scrollIntoView({ block: "start", behavior: "instant" });
  };
  links.forEach((link) => {
    link.addEventListener("focus", () => select(link.hash.slice(1), "push", true));
    link.addEventListener("click", (event) => {
      // Modified clicks keep their native browser behavior.
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      select(link.hash.slice(1), "push", true);
    });
  });
  const fromFragment = () => select(location.hash.slice(1), "none", true);
  window.addEventListener("hashchange", fromFragment);
  window.addEventListener("popstate", fromFragment);
  select(current);
  if (ids.has(location.hash.slice(1))) requestAnimationFrame(fromFragment);

  if (!("IntersectionObserver" in window)) return;
  const ratios = new Map(stages.map((stage) => [stage.id, 0]));
  const trackVisibleStage: IntersectionObserverCallback = (entries) => {
    entries.forEach((entry) => ratios.set(entry.target.id, entry.isIntersecting ? entry.intersectionRatio : 0));
    const maximum = Math.max(...ratios.values());
    if (maximum <= 0) return;
    const tied = stages.filter((stage) => Math.abs((ratios.get(stage.id) ?? 0) - maximum) < 0.001);
    // Preserve the current stage on a tie instead of snapping to the first entry.
    if (!tied.some((stage) => stage.id === current)) select(tied[0].id, "replace");
  };
  let observer: IntersectionObserver | undefined;
  const observeStages = () => {
    observer?.disconnect();
    stages.forEach((stage) => ratios.set(stage.id, 0));
    // Pixel margins avoid percentages being based on root width; rebuild on rotation/resize.
    observer = new IntersectionObserver(trackVisibleStage, {
      threshold: [0, 0.25, 0.5, 0.75, 1], rootMargin: `0px 0px -${Math.round(window.innerHeight * 0.6)}px 0px`
    });
    stages.forEach((stage) => observer!.observe(stage));
  };
  observeStages();
  window.addEventListener("resize", observeStages);
}
