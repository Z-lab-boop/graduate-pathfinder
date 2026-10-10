import { LANGUAGE_KEY, type Language } from "./i18n.js";
import { contentCopy } from "./content.js";
import { initHome } from "./home.js";
import { initExplore } from "./explore.js";

export function applyLanguage(language: Language): void {
  const dictionary: Record<string, string> = contentCopy[language];
  document.documentElement.lang = language;
  document.querySelectorAll<HTMLElement>("[data-i18n]").forEach((element) => {
    const value = dictionary[element.dataset.i18n ?? ""];
    if (value !== undefined) element.textContent = value;
  });
  document.querySelectorAll<HTMLElement>("[data-i18n-label]").forEach((element) => {
    const value = dictionary[element.dataset.i18nLabel ?? ""];
    if (value !== undefined) element.setAttribute("aria-label", value);
  });
  document.querySelectorAll<HTMLImageElement>("[data-i18n-alt]").forEach((element) => {
    const value = dictionary[element.dataset.i18nAlt ?? ""];
    if (value !== undefined) element.alt = value;
  });
  const page = document.body.dataset.page;
  if (page && dictionary[`${page}.title`]) document.title = dictionary[`${page}.title`];
  const description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
  if (description && page && dictionary[`${page}.description`]) description.content = dictionary[`${page}.description`];
  document.dispatchEvent(new CustomEvent("site:language", { detail: language }));
}

export function initSite(): void {
  let language: Language = "en";
  try {
    const stored = localStorage.getItem(LANGUAGE_KEY);
    if (stored === "en" || stored === "zh-CN") language = stored;
  } catch {
    // English static content remains usable when browser storage is unavailable.
  }
  applyLanguage(language);
  initHome();
  void initExplore();
  document.querySelectorAll<HTMLButtonElement>("[data-copy]").forEach((button) => {
    button.hidden = false;
    button.addEventListener("click", async () => {
      const command = document.getElementById(button.dataset.copy ?? "");
      const status = document.querySelector<HTMLElement>("[data-copy-status]");
      if (!command || !status) return;
      let key: "copy.success" | "copy.manual" = "copy.success";
      try {
        await navigator.clipboard.writeText(command.textContent ?? "");
      } catch {
        const range = document.createRange();
        range.selectNodeContents(command);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);
        key = "copy.manual";
      }
      status.dataset.i18n = key;
      status.textContent = contentCopy[language][key];
    });
  });
  document.querySelector<HTMLButtonElement>("[data-language-switch]")?.addEventListener("click", () => {
    language = language === "en" ? "zh-CN" : "en";
    applyLanguage(language);
    try {
      localStorage.setItem(LANGUAGE_KEY, language);
    } catch {
      // A deliberate switch still works for the current page without persistence.
    }
  });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initSite, { once: true });
else initSite();
