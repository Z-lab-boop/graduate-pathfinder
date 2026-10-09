export type EvidenceStatus = "confirmed" | "missing" | "conflicted" | "review_required";
export type OutlookState = "eligible" | "blocked" | "ready" | "repairable" | "reach" | "core" | "safety" | "insufficient" | "high" | "medium" | "low";
export interface DemoMaterial { id: string; label: string; kind: "resume" | "transcript" | "recommendation" | "certificate"; extraction: "reviewed" | "partial" | "unreadable"; evidence: EvidenceStatus; }
export interface DemoTarget { id: string; institution: string; unit: string; program: string; degree: "academic" | "professional"; round: "summer-camp" | "pre-recommendation" | "september"; }
export interface DemoRequirement { id: string; target_id: string; material_id: string; label: string; evidence_id: string; }
export interface DemoEvent { id: string; target_id: string; date: string; label: string; evidence_id: string; }
export interface DemoCount { id: string; target_id: string; stage: "applied" | "interviewed" | "attended" | "admitted"; value: number; scope_id: string; evidence_id: string; }
export type DemoMetric = { id: string; label: string; numerator_id: string; denominator_id: string; state: "matched" } | { id: string; label: string; numerator_id: string; denominator_id: string; state: "refused" };
export interface DemoEvidence { id: string; claim: string; source: string; tier: "synthetic_primary" | "synthetic_note"; status: EvidenceStatus; }
export interface DemoOutlook { target_id: string; eligibility: OutlookState; material_readiness: OutlookState; competitive_tier: OutlookState; fit: OutlookState; confidence: OutlookState; reasons: string[]; }
export interface DemoFix { id: string; requirement_id: string; guidance: string; }
export interface Demo { synthetic: true; materials: DemoMaterial[]; targets: DemoTarget[]; requirements: DemoRequirement[]; events: DemoEvent[]; counts: DemoCount[]; metrics: DemoMetric[]; evidence: DemoEvidence[]; outlooks: DemoOutlook[]; fixes: DemoFix[]; }

const statuses = ["confirmed", "missing", "conflicted", "review_required"];
const institutions = ["Northlake Institute", "Meridian Technical College", "Harborline Academy"];
type Rule = (value: unknown) => void;
function fail(): never { throw new Error("Invalid synthetic walkthrough data"); }
const unsafe = /[<>\u0000-\u001f]|&(?:lt|gt|#\d+|#x[\da-f]+);|(?:https?:|ftp:|www\.|[\w.-]+\.(?:edu|ac\.cn|edu\.cn)\b)|[\w.+-]+@[\w.-]+|(?:^|[\s"'=])(?:\/|~[\/\\]|[a-z]:[\/\\])|\b\d{8,}\b|(?:student[ _-]?(?:id|number)|identity[ _-]?(?:id|number)|学号|身份证|手机号)|\bsk-[\w-]+|\bBearer\s+\S+|["']?(?:api[ _-]?key|access[ _-]?token|refresh[ _-]?token|token|secret|password|credential|session(?:[ _-]?id)?|authorization)["']?\s*[:=]|(?:清华|北京大学|复旦|上海交通|浙江大学|大学|大学院|Peking|Tsinghua|Stanford|Harvard|Oxford|Cambridge|University|\bMIT\b)|\b(?:real|official|authentic)\b/i;
const credentialOrUri = /\b(?:[a-z][\w+.-]*:\/\/|javascript:|data:|file:|mailto:|blob:|tel:)|\b(?:gh[pousr]_|github_pat_|AKIA[0-9A-Z]{12,}|eyJ[\w-]+\.[\w-]+\.[\w-]+)/i;
const schoolMarker = /\b(?:institute|college|academy|school|caltech|princeton|yale)\b|真实院校|真实学校|学院|研究院|\b[\w.-]+\.(?:edu|ac)(?:\.[a-z]{2})?\b/i;
const string: Rule = value => { if (typeof value !== "string" || !value.trim() || value.length > 300 || unsafe.test(value) || credentialOrUri.test(value) || schoolMarker.test(value)) fail(); };
const id: Rule = value => { string(value); if (!/^[a-z][a-z0-9_-]{0,55}$/.test(value as string)) fail(); };
const choice = (values: string[]): Rule => value => { if (typeof value !== "string" || !values.includes(value)) fail(); };
const fields = (value: unknown, rules: Record<string, Rule>): void => {
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype) fail();
  const record = value as Record<string, unknown>;
  if (Object.keys(record).length !== Object.keys(rules).length || Object.keys(record).some(key => !Object.hasOwn(rules, key))) fail();
  for (const [key, rule] of Object.entries(rules)) rule(record[key]);
};
const rules: Record<Exclude<keyof Demo, "synthetic">, Record<string, Rule>> = {
  materials: { id, label: string, kind: choice(["resume", "transcript", "recommendation", "certificate"]), extraction: choice(["reviewed", "partial", "unreadable"]), evidence: choice(statuses) },
  targets: { id, institution: choice(institutions), unit: string, program: string, degree: choice(["academic", "professional"]), round: choice(["summer-camp", "pre-recommendation", "september"]) },
  requirements: { id, target_id: id, material_id: id, label: string, evidence_id: id },
  events: { id, target_id: id, date: value => { string(value); if (!/^2025-\d{2}-\d{2}$/.test(value as string) || Number.isNaN(Date.parse(value as string)) || new Date(value as string).toISOString().slice(0, 10) !== value) fail(); }, label: string, evidence_id: id },
  counts: { id, target_id: id, stage: choice(["applied", "interviewed", "attended", "admitted"]), value: value => { if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0 || value > 1_000_000) fail(); }, scope_id: id, evidence_id: id },
  metrics: { id, label: string, numerator_id: id, denominator_id: id, state: choice(["matched", "refused"]) },
  evidence: { id, claim: string, source: string, tier: choice(["synthetic_primary", "synthetic_note"]), status: choice(statuses) },
  outlooks: { target_id: id, eligibility: choice(["eligible", "blocked", "insufficient"]), material_readiness: choice(["ready", "repairable", "blocked", "insufficient"]), competitive_tier: choice(["reach", "core", "safety", "insufficient"]), fit: choice(["high", "medium", "low", "insufficient"]), confidence: choice(["high", "medium", "low", "insufficient"]), reasons: value => { if (!Array.isArray(value) || value.length < 1 || value.length > 8) fail(); value.forEach(string); } },
  fixes: { id, requirement_id: id, guidance: value => { string(value); if (/\b(?:apply|submit)\b|提交|投递/i.test(value as string)) fail(); } }
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
  for (const metric of result.metrics) {
    const numerator = ref(result.counts, metric.numerator_id) as DemoCount;
    const denominator = ref(result.counts, metric.denominator_id) as DemoCount;
    const scopesMatch = numerator.target_id === denominator.target_id && numerator.scope_id === denominator.scope_id;
    if ((metric.state === "matched") !== scopesMatch || (scopesMatch && (denominator.value === 0 || numerator.value > denominator.value || numerator.stage !== "admitted" || denominator.stage !== "interviewed" || [numerator, denominator].some(count => (ref(result.evidence, count.evidence_id) as DemoEvidence).status !== "confirmed")))) fail();
  }
  for (const target of result.targets) {
    if (result.outlooks.filter(item => item.target_id === target.id).length !== 1 || !result.requirements.some(item => item.target_id === target.id)) fail();
  }
  result.outlooks.forEach(item => ref(result.targets, item.target_id));
  return result;
}
