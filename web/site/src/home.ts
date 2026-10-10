export function initHome(): void {
  const journey = document.querySelector<HTMLElement>("[data-journey]");
  if (!journey || journey.dataset.initialized) return;
  journey.dataset.initialized = "true";
  const links = Array.from(journey.querySelectorAll<HTMLAnchorElement>("[data-stage-link]"));
  const stages = Array.from(document.querySelectorAll<HTMLElement>("[data-stage]"));
  const ids = new Set(stages.map((stage) => stage.id));
  let current = ids.has(location.hash.slice(1)) ? location.hash.slice(1) : "profile";
  let fragmentTarget: string | null = ids.has(location.hash.slice(1)) ? current : null;
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
  const fromFragment = () => {
    const id = location.hash.slice(1);
    if (!ids.has(id)) return;
    fragmentTarget = id;
    select(id, "none", true);
  };
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
    // Fragment navigation owns the selection until its programmatic scroll settles.
    if (fragmentTarget && !tied.some((stage) => stage.id === fragmentTarget)) return;
    fragmentTarget = null;
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
