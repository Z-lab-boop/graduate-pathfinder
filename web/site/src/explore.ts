import { parseDemo, type Demo, type DemoEvidence, type DemoRequirement, type EvidenceStatus } from "./demo-schema.js";

const chinese: Record<string, string> = {
  "Fictional institutions only": "以下院校均为虚构", "Select a fictional target": "选择虚构目标", "Synthetic admissions case": "合成招生案例",
  "Northlake Institute": "虚构·北湖研究院", "Data Systems": "数据系统", "Meridian Technical College": "虚构·子午技术学院", "Intelligent Systems": "智能系统", "Harborline Academy": "虚构·港线学园", "Human-Centered Computing": "人本计算",
  "Data Methods": "数据方法", "Interactive Engineering": "交互工程", "Design Computing": "设计计算", "academic": "学术学位", "professional": "专业学位", "summer-camp": "夏令营", "pre-recommendation": "预推免", "september": "九月推免",
  "Materials": "材料", "Targets": "目标", "Previous cycle": "上年度", "Outlook": "展望", "Case views": "案例视图", "Evidence filters": "证据筛选", "Confirmed": "已确认", "Missing": "缺失", "Conflicted": "有冲突", "Review required": "需复核",
  "Evidence inspector": "证据检查器", "Select a record to inspect its source claim.": "选择记录，查看其来源主张。", "Source": "来源", "Claim": "主张", "Tier": "层级", "Synthetic primary": "合成一手记录", "Synthetic note": "合成复核记录",
  "Target requirements": "目标材料要求", "Material": "材料", "Extraction": "提取状态", "Requirement / evidence": "要求与证据", "No records match these evidence filters.": "没有记录符合当前证据筛选。", "Six anonymous materials · target-specific requirements": "六份匿名材料 · 按目标复核要求", "Inspect evidence": "检查证据", "Preview guidance": "预览指导",
  "Anonymous resume": "匿名简历", "Course transcript": "课程成绩单", "Unsigned letter draft": "未签字的推荐信草稿", "Language certificate": "语言证书", "Project certificate": "项目证明", "Ranking supplement": "排名补充材料", "reviewed": "已复核", "partial": "部分提取", "unreadable": "无法读取",
  "Reviewed resume required": "需要已复核的简历", "Signed recommendation required": "需要签字推荐信", "Resolve certificate date conflict": "解决证书日期冲突", "Review unreadable project evidence": "复核无法读取的项目证据", "Review ranking supplement": "复核排名补充材料", "Reviewed transcript required": "需要已复核的成绩单",
  "Resume extraction was reviewed in this fictional case.": "本虚构案例已复核简历提取结果。", "Transcript fields were reviewed in this fictional case.": "本虚构案例已复核成绩单字段。", "The recommendation is a draft and lacks a signature.": "推荐信仍为草稿，缺少签字。", "Two fictional certificate dates disagree.": "两份虚构证书日期存在冲突。", "The project certificate extraction is unreadable.": "项目证明提取结果无法读取。", "The ranking denominator needs manual review.": "排名分母需要人工复核。", "Counts share one fictional intake, route and unit scope.": "人数属于同一虚构入学年、路径与单位口径。", "Attendance belongs to a different fictional route scope.": "参加人数属于另一虚构申请路径口径。",
  "Fictional material review sheet": "虚构材料复核表", "Fictional recommendation checklist": "虚构推荐信清单", "Fictional conflict register": "虚构冲突记录", "Fictional extraction review": "虚构提取复核", "Fictional cycle register": "虚构周期记录", "Fictional alternate cycle register": "虚构其他路径记录",
  "Target comparison": "目标比较", "Choose a target to update every view.": "选择目标以同步更新各视图。", "Admission outlook": "录取展望", "Eligibility": "资格", "Material readiness": "材料就绪度", "Competitive tier": "竞争序数档位", "Fit": "适配", "Evidence confidence": "证据信心", "Independent dimensions · no combined score": "独立维度 · 不合成为总分",
  "eligible": "符合", "blocked": "受阻", "ready": "就绪", "repairable": "可修复", "reach": "冲刺", "core": "主申", "safety": "保守", "insufficient": "证据不足", "high": "高", "medium": "中", "low": "低",
  "Unsigned draft blocks material readiness.": "未签字草稿阻碍材料就绪。", "Certificate conflict limits evidence confidence.": "证书冲突限制证据信心。", "Ranking denominator needs review.": "排名分母需要复核。", "Unreadable evidence leaves a required gate unresolved.": "无法读取的证据使必要门槛尚未解决。",
  "Past cohort description · not personal probability": "历史群体描述 · 非个人录取概率", "Scoped stage counts": "按口径区分的阶段人数", "Timeline": "时间线", "Scope": "口径", "Numerator": "分子", "Denominator": "分母", "Refused: stage scopes do not match": "拒绝计算：阶段口径不匹配", "No previous-cycle evidence for this fictional target.": "此虚构目标没有上年度证据。", "Applied": "申请", "Interviewed": "面试", "Attended": "参加", "Admitted": "录取",
  "Fictional announcement": "虚构公告", "Fictional interviews": "虚构面试", "Fictional cohort recorded": "虚构群体记录", "Admitted among interviewed": "面试群体中的录取人数", "Admitted among alternate-route attendees": "其他路径参加群体中的录取人数", "northlake-data-summer-2025": "北湖-数据-夏令营-2025", "northlake-data-alternate-2025": "北湖-数据-其他路径-2025",
  "Guidance only": "仅供指导", "Close preview": "关闭预览", "This preview changes no material or evidence.": "此预览不会修改材料或证据。", "Review the draft with its fictional author and check the signature field locally.": "在本地与虚构作者复核草稿，并检查签字字段。", "Recheck the fictional source image and record unresolved extraction fields locally.": "重新核对虚构源图，在本地记录未解决的提取字段。",
  "Walkthrough unavailable": "演示暂不可用", "The committed fictional case could not be validated. No partial results are shown.": "已提交的虚构案例未能通过校验，未显示部分结果。", "Read the expected behavior": "阅读预期行为", "Close the preview to change the case language.": "关闭预览后可切换案例语言。"
};
const statusLabels: Record<EvidenceStatus, string> = { confirmed: "Confirmed", missing: "Missing", conflicted: "Conflicted", review_required: "Review required" };
const dimensions = [["eligibility", "Eligibility"], ["material_readiness", "Material readiness"], ["competitive_tier", "Competitive tier"], ["fit", "Fit"], ["confidence", "Evidence confidence"]] as const;
const tabs = ["Materials", "Targets", "Previous cycle", "Outlook"];
const targetOrder = ["target-northlake", "target-meridian", "target-harborline"];
const stages = ["applied", "interviewed", "attended", "admitted"];

function element<K extends keyof HTMLElementTagNameMap>(tag: K, text?: string, className?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

/** Client-only walkthrough. Validate once, then coordinate all views from one local state. */
export async function initExplore(): Promise<void> {
  const root = document.querySelector<HTMLElement>("#walkthrough");
  if (!root) return;
  let data: Demo | undefined;
  let targetId = "target-northlake";
  let tab = "Materials";
  let evidenceId: string | undefined;
  let previewId: string | undefined;
  const filters = new Set<EvidenceStatus>(Object.keys(statusLabels) as EvidenceStatus[]);
  const tr = (value: string) => document.documentElement.lang === "zh-CN" ? chinese[value] ?? value : value;
  const button = (text: string, control: string, action: () => void) => {
    const node = element("button", text); node.type = "button"; node.dataset.control = control;
    node.addEventListener("click", action); return node;
  };
  const inspect = (identifier: string) => {
    evidenceId = identifier; render();
    root.querySelector<HTMLElement>(".case-inspector")?.scrollIntoView({ block: "nearest", behavior: "instant" });
  };
  const evidence = (identifier: string) => data!.evidence.find(item => item.id === identifier)!;
  const visible = (identifier: string) => filters.has(evidence(identifier).status);
  const targetName = (identifier: string) => { const target = data!.targets.find(item => item.id === identifier)!; return `${tr(target.institution)} · ${tr(target.unit)}`; };
  function navigationKeys(container: HTMLElement, selector: string, vertical = false): void {
    container.addEventListener("keydown", event => {
      if (!["ArrowRight", "ArrowLeft", "ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
      if (vertical ? ["ArrowRight", "ArrowLeft"].includes(event.key) : ["ArrowDown", "ArrowUp"].includes(event.key)) return;
      const items = [...container.querySelectorAll<HTMLButtonElement>(selector)];
      const index = items.indexOf(document.activeElement as HTMLButtonElement);
      if (index < 0) return;
      event.preventDefault();
      const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (index + (["ArrowRight", "ArrowDown"].includes(event.key) ? 1 : -1) + items.length) % items.length;
      items[next].click();
      root!.querySelector<HTMLButtonElement>(`[data-control="${items[next].dataset.control}"]`)?.focus();
    });
  }
  function unavailable(): void {
    root!.replaceChildren(element("h2", tr("Walkthrough unavailable")), element("p", tr("The committed fictional case could not be validated. No partial results are shown.")));
    const link = element("a", tr("Read the expected behavior"));
    link.href = "https://github.com/Z-lab-boop/graduate-pathfinder/blob/main/tests/fixtures/baoyan_case/expected-behavior.md";
    root!.append(link); root!.setAttribute("aria-busy", "false");
  }
  function badge(record: DemoEvidence): HTMLElement { return element("span", tr(statusLabels[record.status]), `evidence-badge evidence-${record.status}`); }
  function inspectionButton(identifier: string, control: string): HTMLButtonElement { return button(tr("Inspect evidence"), control, () => inspect(identifier)); }
  function render(): void {
    if (!data) { unavailable(); return; }
    const active = (document.activeElement as HTMLElement | null)?.dataset.control;
    const scroll = window.scrollY;
    root!.replaceChildren();
    root!.setAttribute("aria-label", tr("Synthetic admissions case"));
    root!.setAttribute("aria-busy", "false");
    const rail = element("aside", undefined, "target-rail");
    rail.setAttribute("aria-label", tr("Select a fictional target"));
    rail.append(element("p", tr("Fictional institutions only"), "eyebrow"));
    const list = element("ul");
    for (const identifier of targetOrder) {
      const item = element("li");
      const control = button(targetName(identifier), identifier, () => { targetId = identifier; evidenceId = undefined; render(); });
      control.dataset.target = identifier; control.setAttribute("aria-pressed", String(identifier === targetId));
      control.tabIndex = identifier === targetId ? 0 : -1;
      item.append(control); list.append(item);
    }
    rail.append(list); navigationKeys(rail, "[data-target]", true);
    const content = element("div", undefined, "case-workspace");
    const tablist = element("div", undefined, "case-tabs"); tablist.setAttribute("role", "tablist"); tablist.setAttribute("aria-label", tr("Case views"));
    for (const [index, name] of tabs.entries()) {
      const control = button(tr(name), `tab-${index}`, () => { tab = name; render(); });
      control.id = `case-tab-${index}`; control.setAttribute("role", "tab"); control.setAttribute("aria-selected", String(name === tab));
      control.setAttribute("aria-controls", "case-panel"); control.tabIndex = name === tab ? 0 : -1; tablist.append(control);
    }
    navigationKeys(tablist, "[role=tab]");
    const filterset = element("fieldset", undefined, "case-filters"); filterset.append(element("legend", tr("Evidence filters")));
    for (const status of Object.keys(statusLabels) as EvidenceStatus[]) {
      const label = element("label"); const input = element("input"); input.type = "checkbox"; input.checked = filters.has(status); input.dataset.control = `filter-${status}`;
      input.addEventListener("change", () => { input.checked ? filters.add(status) : filters.delete(status); if (evidenceId && !visible(evidenceId)) evidenceId = undefined; render(); });
      label.append(input, document.createTextNode(tr(statusLabels[status]))); filterset.append(label);
    }
    const panel = element("section", undefined, "case-panel"); panel.id = "case-panel"; panel.setAttribute("role", "tabpanel"); panel.setAttribute("aria-labelledby", `case-tab-${tabs.indexOf(tab)}`); panel.tabIndex = 0;
    panel.append(element("p", targetName(targetId), "case-target-heading"));
    if (tab === "Materials") renderMaterials(panel);
    if (tab === "Targets") renderTargets(panel);
    if (tab === "Previous cycle") renderHistory(panel);
    if (tab === "Outlook") renderOutlook(panel);
    content.append(tablist, filterset, panel);
    const inspector = element("aside", undefined, "case-inspector"); inspector.setAttribute("aria-label", tr("Evidence inspector")); inspector.setAttribute("aria-live", "polite");
    inspector.append(element("h2", tr("Evidence inspector")));
    if (evidenceId) {
      const record = evidence(evidenceId); const details = element("dl");
      for (const [term, value] of [["Source", record.source], ["Claim", record.claim], ["Tier", record.tier === "synthetic_primary" ? "Synthetic primary" : "Synthetic note"]]) details.append(element("dt", tr(term)), element("dd", tr(value)));
      inspector.append(badge(record), details);
    } else inspector.append(element("p", tr("Select a record to inspect its source claim.")));
    const layout = element("div", undefined, "walkthrough-layout"); layout.append(rail, content, inspector); root!.append(layout);
    if (previewId) renderPreview();
    else if (active) root!.querySelector<HTMLElement>(`[data-control="${active}"]`)?.focus({ preventScroll: true });
    window.scrollTo({ top: scroll, behavior: "instant" });
  }
  function empty(panel: HTMLElement): void { panel.append(element("p", tr("No records match these evidence filters."), "case-empty")); }
  function guidance(requirement: DemoRequirement): HTMLButtonElement | undefined {
    const fix = data!.fixes.find(item => item.requirement_id === requirement.id);
    return fix ? button(tr("Preview guidance"), fix.id, () => { previewId = fix.id; render(); }) : undefined;
  }
  function renderMaterials(panel: HTMLElement): void {
    panel.append(element("h2", tr("Target requirements")), element("p", tr("Six anonymous materials · target-specific requirements")));
    const rows = data!.requirements.filter(item => item.target_id === targetId && visible(item.evidence_id));
    if (!rows.length) { empty(panel); return; }
    const table = element("table", undefined, "materials-matrix");
    const head = element("thead"); const headers = element("tr");
    for (const title of ["Material", "Extraction", "Requirement / evidence"]) { const cell = element("th", tr(title)); cell.scope = "col"; headers.append(cell); }
    head.append(headers); const body = element("tbody");
    for (const requirement of rows) {
      const material = data!.materials.find(item => item.id === requirement.material_id)!;
      const row = element("tr"); row.dataset.record = requirement.id;
      const name = element("th", tr(material.label)); name.scope = "row";
      const cell = element("td"); cell.append(element("p", tr(requirement.label)), badge(evidence(requirement.evidence_id)), inspectionButton(requirement.evidence_id, requirement.id));
      const preview = guidance(requirement); if (preview) cell.append(preview);
      row.append(name, element("td", tr(material.extraction)), cell); body.append(row);
    }
    table.append(head, body); panel.append(table);
  }
  function renderTargets(panel: HTMLElement): void {
    panel.append(element("h2", tr("Target comparison")), element("p", tr("Choose a target to update every view.")));
    const target = data!.targets.find(item => item.id === targetId)!;
    panel.append(element("p", `${tr(target.program)} · ${tr(target.degree)} · ${tr(target.round)}`));
    renderOutlook(panel);
    const list = element("ul", undefined, "case-records");
    for (const requirement of data!.requirements.filter(item => item.target_id === targetId && visible(item.evidence_id))) {
      const item = element("li"); item.dataset.record = requirement.id;
      item.append(element("span", tr(requirement.label)), badge(evidence(requirement.evidence_id)), inspectionButton(requirement.evidence_id, requirement.id)); list.append(item);
    }
    list.childElementCount ? panel.append(list) : empty(panel);
  }
  function renderOutlook(panel: HTMLElement): void {
    const outlook = data!.outlooks.find(item => item.target_id === targetId)!;
    const section = element("section", undefined, "outlook-view"); section.setAttribute("aria-label", tr("Admission outlook"));
    section.append(element("h2", tr("Admission outlook")), element("p", tr("Independent dimensions · no combined score")));
    const list = element("dl", undefined, "outlook-axes");
    for (const [field, label] of dimensions) {
      const row = element("div"); row.append(element("dt", tr(label)), element("dd", tr(outlook[field]))); list.append(row);
    }
    const reasons = element("ul"); outlook.reasons.forEach(reason => reasons.append(element("li", tr(reason))));
    section.append(list, reasons); panel.append(section);
  }
  function renderHistory(panel: HTMLElement): void {
    panel.append(element("h2", tr("Previous cycle")), element("p", tr("Past cohort description · not personal probability"), "history-warning"));
    const counts = data!.counts.filter(item => item.target_id === targetId && visible(item.evidence_id)).sort((a, b) => stages.indexOf(a.stage) - stages.indexOf(b.stage));
    if (!data!.counts.some(item => item.target_id === targetId)) { panel.append(element("p", tr("No previous-cycle evidence for this fictional target."))); return; }
    if (!counts.length) { empty(panel); return; }
    panel.append(element("h3", tr("Timeline")));
    const timeline = element("ol", undefined, "case-timeline");
    data!.events.filter(item => item.target_id === targetId && visible(item.evidence_id)).sort((a, b) => a.date.localeCompare(b.date)).forEach(event => {
      const item = element("li"); item.dataset.record = event.id;
      const date = element("time", event.date); date.dateTime = event.date;
      item.append(date, button(tr(event.label), event.id, () => inspect(event.evidence_id))); timeline.append(item);
    });
    panel.append(timeline, element("h3", tr("Scoped stage counts")));
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("viewBox", "0 0 480 140"); svg.setAttribute("aria-hidden", "true"); svg.classList.add("stage-diagram");
    const list = element("ul", undefined, "stage-equivalents");
    for (const [index, count] of counts.entries()) {
      const label = `${tr(count.stage[0].toUpperCase() + count.stage.slice(1))} · ${count.value}`;
      const group = document.createElementNS(svg.namespaceURI, "g");
      const rect = document.createElementNS(svg.namespaceURI, "rect"); rect.setAttribute("x", String(index * 120 + 12)); rect.setAttribute("y", String(100 - count.value)); rect.setAttribute("width", "85"); rect.setAttribute("height", String(count.value));
      const text = document.createElementNS(svg.namespaceURI, "text"); text.setAttribute("x", String(index * 120 + 12)); text.setAttribute("y", "125"); text.textContent = String(count.value);
      group.append(rect, text); group.addEventListener("click", () => inspect(count.evidence_id)); svg.append(group);
      const item = element("li"); item.dataset.record = count.id;
      item.append(button(label, count.id, () => inspect(count.evidence_id)), element("p", `${tr("Scope")}: ${tr(count.scope_id)}`)); list.append(item);
    }
    panel.append(svg, list);
    for (const metric of data!.metrics) {
      const numerator = data!.counts.find(item => item.id === metric.numerator_id)!;
      const denominator = data!.counts.find(item => item.id === metric.denominator_id)!;
      if (numerator.target_id !== targetId || !visible(numerator.evidence_id) || !visible(denominator.evidence_id)) continue;
      const record = element("section", undefined, "history-metric"); record.dataset.record = metric.id;
      record.append(element("h3", tr(metric.label)), element("p", `${tr("Numerator")}: ${numerator.value} · ${tr(numerator.scope_id)}`), element("p", `${tr("Denominator")}: ${denominator.value} · ${tr(denominator.scope_id)}`));
      record.append(element("p", metric.state === "matched" ? `${numerator.value} / ${denominator.value} = ${Math.round(numerator.value / denominator.value * 100)}%` : tr("Refused: stage scopes do not match"), metric.state === "matched" ? "metric-result" : "metric-refused"));
      panel.append(record);
    }
  }
  function renderPreview(): void {
    const fix = data!.fixes.find(item => item.id === previewId)!;
    const dialog = element("dialog", undefined, "guidance-preview"); dialog.setAttribute("aria-labelledby", "preview-heading");
    const stamp = element("p", "Synthetic walkthrough / 合成演示", "synthetic-label");
    const heading = element("h2", tr("Guidance only")); heading.id = "preview-heading";
    dialog.append(stamp, heading, element("p", tr(fix.guidance)), element("p", tr("This preview changes no material or evidence.")), element("p", tr("Close the preview to change the case language.")));
    const close = button(tr("Close preview"), "close-preview", () => dialog.close()); dialog.append(close);
    dialog.addEventListener("close", () => { const identifier = previewId; previewId = undefined; render(); root!.querySelector<HTMLElement>(`[data-control="${identifier}"]`)?.focus({ preventScroll: true }); });
    root!.append(dialog); dialog.showModal(); close.focus();
  }
  document.addEventListener("site:language", () => data ? render() : unavailable());
  try {
    const response = await fetch("./data/demo.json", { method: "GET", credentials: "omit", mode: "same-origin", redirect: "error" });
    if (!response.ok) throw new Error("Demo unavailable");
    data = parseDemo(await response.json());
    render();
  } catch { data = undefined; evidenceId = undefined; previewId = undefined; unavailable(); }
}
