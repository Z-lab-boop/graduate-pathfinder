export type EvidenceStatus = "confirmed" | "missing" | "conflicted" | "review_required";
export type CompetitiveTier = "strong" | "competitive" | "borderline" | "weak" | "evidence_insufficient";
export type OutlookState = "eligible" | "blocked" | "ready" | "repairable" | "insufficient" | "high" | "medium" | "low";
export interface DemoMaterial { id: string; label: string; kind: "resume" | "transcript" | "recommendation" | "certificate"; extraction: "reviewed" | "partial" | "unreadable"; evidence: EvidenceStatus; }
export interface DemoTarget { id: string; institution: string; unit: string; program: string; degree: "academic" | "professional"; round: "summer-camp" | "pre-recommendation" | "september"; }
export interface DemoRequirement { id: string; target_id: string; material_id: string; label: string; evidence_id: string; }
export interface DemoEvent { id: string; target_id: string; date: string; label: string; evidence_id: string; }
export interface DemoScope { id: string; admission_year: number; institution: string; unit: string; program_code: string; degree_type: "academic" | "professional"; research_track: string; admission_round: "summer-camp" | "pre-recommendation" | "september"; }
export type CountStage = "announced_quota" | "reported_applicants" | "listed_shortlist" | "deduplicated_shortlist" | "confirmed_attended" | "excellent_campers" | "pre_admit" | "waitlist" | "final_admitted";
export interface DemoCount { id: string; target_id: string; stage: CountStage; value: number; scope_id: string; evidence_id: string; }
export type DemoMetric = { id: string; label: string; numerator_id: string; denominator_id: string; state: "matched" } | { id: string; label: string; numerator_id: string; denominator_id: string; state: "refused" };
export interface DemoEvidence { id: string; claim: string; source: string; tier: "synthetic_primary" | "synthetic_note"; status: EvidenceStatus; }
export interface DemoOutlook { target_id: string; eligibility: OutlookState; material_readiness: OutlookState; competitive_tier: CompetitiveTier; fit: OutlookState; confidence: OutlookState; reasons: string[]; }
export interface DemoFix { id: string; requirement_id: string; guidance: string; }
export interface Demo { synthetic: true; materials: DemoMaterial[]; targets: DemoTarget[]; requirements: DemoRequirement[]; events: DemoEvent[]; scopes: DemoScope[]; counts: DemoCount[]; metrics: DemoMetric[]; evidence: DemoEvidence[]; outlooks: DemoOutlook[]; fixes: DemoFix[]; }

const statuses = ["confirmed", "missing", "conflicted", "review_required"];
const institutions = ["Northlake Institute", "Meridian Technical College", "Harborline Academy"];
const scopeTemplates: DemoScope[] = ["summer", "alternate"].map(route => ({
  id: `northlake-data-${route}-2025`, admission_year: 2025, institution: "Northlake Institute", unit: "Data Systems", program_code: "synthetic-data-methods", degree_type: "academic", research_track: "Data Methods", admission_round: route === "summer" ? "summer-camp" : "pre-recommendation"
}));
const scopeFields = ["admission_year", "institution", "unit", "program_code", "degree_type", "research_track", "admission_round"] as const;
const fixtureIds = new Set([
  "material-resume", "material-transcript", "material-recommendation", "material-language", "material-project", "material-ranking",
  "target-northlake", "target-meridian", "target-harborline",
  "requirement-northlake-resume", "requirement-northlake-letter", "requirement-northlake-language", "requirement-northlake-project",
  "requirement-meridian-resume", "requirement-meridian-letter", "requirement-meridian-language", "requirement-meridian-ranking", "requirement-harborline-transcript", "requirement-harborline-project",
  "evidence-resume", "evidence-transcript", "evidence-letter", "evidence-language", "evidence-project", "evidence-ranking", "evidence-cycle", "evidence-other-cycle",
  "event-announcement", "event-interview", "event-result", "count-applied", "count-confirmed-attended", "count-alternate-attended", "count-final-admitted", "metric-matched", "metric-refused", "fix-northlake-letter", "fix-meridian-letter", "fix-harborline-project", ...scopeTemplates.map(scope => scope.id)
]);
type Rule = (value: unknown) => void;
function fail(): never { throw new Error("Invalid synthetic walkthrough data"); }
const unsafe = /[<>\u0000-\u001f]|&(?:lt|gt|#\d+|#x[\da-f]+);|(?:https?:|ftp:|www\.|[\w.-]+\.(?:edu|ac\.cn|edu\.cn)\b)|[\w.+-]+@[\w.-]+|(?:^|[\s"'=])(?:\/|~[\/\\]|[a-z]:[\/\\])|\b\d{8,}\b|(?:student[ _-]?(?:id|number)|identity[ _-]?(?:id|number)|学号|身份证|手机号)|\bsk-[\w-]+|\bBearer\s+\S+|["']?(?:api[ _-]?key|access[ _-]?token|refresh[ _-]?token|token|secret|password|credential|session(?:[ _-]?id)?|authorization)["']?\s*[:=]|(?:清华|北京大学|复旦|上海交通|浙江大学|大学|大学院|Peking|Tsinghua|Stanford|Harvard|Oxford|Cambridge|University|\bMIT\b)|\b(?:real|official|authentic)\b/i;
const credentialOrUri = /\b(?:[a-z][\w+.-]*:\/\/|javascript:|data:|file:|mailto:|blob:|tel:)|\b(?:gh[pousr]_|github_pat_|AKIA[0-9A-Z]{12,}|eyJ[\w-]+\.[\w-]+\.[\w-]+)/i;
const schoolMarker = /\b(?:institute|college|academy|school|caltech|princeton|yale)\b|真实院校|真实学校|学院|研究院|\b[\w.-]+\.(?:edu|ac)(?:\.[a-z]{2})?\b/i;
const string: Rule = value => { if (typeof value !== "string" || !value.trim() || value.length > 300 || unsafe.test(value) || credentialOrUri.test(value) || schoolMarker.test(value)) fail(); };
const id: Rule = value => { string(value); if (!fixtureIds.has(value as string)) fail(); };
const choice = (values: string[]): Rule => value => { if (typeof value !== "string" || !values.includes(value)) fail(); };
// Public fixture corpus: no arbitrary display string is accepted. Extending the
// committed case requires an explicit schema and bilingual-copy review.
const text = choice([
  "Anonymous resume", "Course transcript", "Unsigned letter draft", "Language certificate", "Project certificate", "Ranking supplement",
  "Data Systems", "Intelligent Systems", "Human-Centered Computing", "Data Methods", "Interactive Engineering", "Design Computing", "synthetic-data-methods",
  "Reviewed resume required", "Signed recommendation required", "Resolve certificate date conflict", "Review unreadable project evidence", "Review ranking supplement", "Reviewed transcript required",
  "Resume extraction was reviewed in this fictional case.", "Transcript fields were reviewed in this fictional case.", "The recommendation is a draft and lacks a signature.", "Two fictional certificate dates disagree.", "The project certificate extraction is unreadable.", "The ranking denominator needs manual review.", "Counts share one fictional intake, route and unit scope.", "Attendance belongs to a different fictional route scope.",
  "Fictional material review sheet", "Fictional recommendation checklist", "Fictional conflict register", "Fictional extraction review", "Fictional cycle register", "Fictional alternate cycle register",
  "Fictional announcement", "Fictional interviews", "Fictional cohort recorded", "Final admitted among confirmed attendees", "Final admitted among alternate-route confirmed attendees",
  "Unsigned draft blocks material readiness.", "Certificate conflict limits evidence confidence.", "Ranking denominator needs review.", "Unreadable evidence leaves a required gate unresolved.", "Current competitive evidence is missing.", "Comparable history and current competitive evidence are missing.",
  "Review the draft with its fictional author and check the signature field locally.", "Recheck the fictional source image and record unresolved extraction fields locally."
]);
const fields = (value: unknown, rules: Record<string, Rule>): void => {
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype) fail();
  const record = value as Record<string, unknown>;
  if (Object.keys(record).length !== Object.keys(rules).length || Object.keys(record).some(key => !Object.hasOwn(rules, key))) fail();
  for (const [key, rule] of Object.entries(rules)) rule(record[key]);
};
const rules: Record<Exclude<keyof Demo, "synthetic">, Record<string, Rule>> = {
  materials: { id, label: text, kind: choice(["resume", "transcript", "recommendation", "certificate"]), extraction: choice(["reviewed", "partial", "unreadable"]), evidence: choice(statuses) },
  targets: { id, institution: choice(institutions), unit: text, program: text, degree: choice(["academic", "professional"]), round: choice(["summer-camp", "pre-recommendation", "september"]) },
  requirements: { id, target_id: id, material_id: id, label: text, evidence_id: id },
  events: { id, target_id: id, date: choice(["2025-06-02", "2025-07-08", "2025-07-20"]), label: text, evidence_id: id },
  scopes: { id, admission_year: value => { if (value !== 2025) fail(); }, institution: choice(institutions), unit: text, program_code: text, degree_type: choice(["academic", "professional"]), research_track: text, admission_round: choice(["summer-camp", "pre-recommendation", "september"]) },
  counts: { id, target_id: id, stage: choice(["announced_quota", "reported_applicants", "listed_shortlist", "deduplicated_shortlist", "confirmed_attended", "excellent_campers", "pre_admit", "waitlist", "final_admitted"]), value: value => { if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0 || value > 1_000_000) fail(); }, scope_id: id, evidence_id: id },
  metrics: { id, label: text, numerator_id: id, denominator_id: id, state: choice(["matched", "refused"]) },
  evidence: { id, claim: text, source: text, tier: choice(["synthetic_primary", "synthetic_note"]), status: choice(statuses) },
  outlooks: { target_id: id, eligibility: choice(["eligible", "blocked", "insufficient"]), material_readiness: choice(["ready", "repairable", "blocked", "insufficient"]), competitive_tier: choice(["strong", "competitive", "borderline", "weak", "evidence_insufficient"]), fit: choice(["high", "medium", "low", "insufficient"]), confidence: choice(["high", "medium", "low", "insufficient"]), reasons: value => { if (!Array.isArray(value) || value.length < 1 || value.length > 8) fail(); value.forEach(text); } },
  fixes: { id, requirement_id: id, guidance: text }
};

/** Validate the whole file before any rendering. No input object survives by reference. */
export function parseDemo(input: unknown): Demo {
  const rootRules: Record<string, Rule> = { synthetic: value => { if (value !== true) fail(); } };
  for (const [collection, shape] of Object.entries(rules)) rootRules[collection] = value => {
    if (!Array.isArray(value) || !value.length || value.length > 100) fail();
    value.forEach(item => fields(item, shape));
  };
  fields(input, rootRules);
  const result = structuredClone(input) as Demo;
  const globalIds = new Set<string>();
  for (const [key, value] of Object.entries(result)) if (Array.isArray(value)) {
    const seen = new Set<string>();
    for (const item of value) {
      const identifier = "id" in item ? item.id : item.target_id;
      if (seen.has(identifier) || ("id" in item && globalIds.has(identifier))) fail();
      seen.add(identifier); if ("id" in item) globalIds.add(identifier);
    }
    value.sort((a, b) => ("id" in a ? a.id : a.target_id).localeCompare("id" in b ? b.id : b.target_id, "en"));
    if (key === "outlooks") value.forEach(item => item.reasons.sort());
  }
  const ref = (collection: { id: string }[], identifier: string) => { const found = collection.find(item => item.id === identifier); if (!found) fail(); return found; };
  for (const record of [...result.requirements, ...result.events, ...result.counts]) {
    ref(result.targets, record.target_id); ref(result.evidence, record.evidence_id);
  }
  result.requirements.forEach(item => ref(result.materials, item.material_id));
  result.fixes.forEach(item => ref(result.requirements, item.requirement_id));
  for (const scope of result.scopes) {
    const template = ref(scopeTemplates, scope.id) as DemoScope;
    if (scopeFields.some(field => scope[field] !== template[field])) fail();
  }
  for (const count of result.counts) {
    const scope = ref(result.scopes, count.scope_id) as DemoScope;
    const target = ref(result.targets, count.target_id) as DemoTarget;
    if (scope.institution !== target.institution || scope.unit !== target.unit || scope.degree_type !== target.degree || scope.research_track !== target.program) fail();
  }
  for (const metric of result.metrics) {
    const numerator = ref(result.counts, metric.numerator_id) as DemoCount;
    const denominator = ref(result.counts, metric.denominator_id) as DemoCount;
    const numeratorScope = ref(result.scopes, numerator.scope_id) as DemoScope;
    const denominatorScope = ref(result.scopes, denominator.scope_id) as DemoScope;
    const scopesMatch = numerator.target_id === denominator.target_id && scopeFields.every(field => numeratorScope[field] === denominatorScope[field]);
    const target = ref(result.targets, numerator.target_id) as DemoTarget;
    if (numerator.stage !== "final_admitted" || denominator.stage !== "confirmed_attended" || (metric.state === "matched") !== scopesMatch || (scopesMatch && (numeratorScope.admission_round !== target.round || denominator.value === 0 || numerator.value > denominator.value || [numerator, denominator].some(count => (ref(result.evidence, count.evidence_id) as DemoEvidence).status !== "confirmed")))) fail();
    if (metric.state === "matched") {
      const sameScopeCounts = result.counts.filter(count => {
        const scope = ref(result.scopes, count.scope_id) as DemoScope;
        return scopeFields.every(field => scope[field] === numeratorScope[field]);
      });
      if (["final_admitted", "confirmed_attended"].some(stage => sameScopeCounts.filter(count => count.stage === stage).length !== 1)) {
        throw new Error("ambiguous_stage_count");
      }
    }
  }
  for (const target of result.targets) {
    if (result.outlooks.filter(item => item.target_id === target.id).length !== 1 || !result.requirements.some(item => item.target_id === target.id)) fail();
  }
  result.outlooks.forEach(item => ref(result.targets, item.target_id));
  return result;
}
