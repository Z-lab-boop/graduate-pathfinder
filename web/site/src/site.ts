import { copy, LANGUAGE_KEY, type Language } from "./i18n.js";

export function applyLanguage(language: Language): void {
  const dictionary = copy[language];
  document.documentElement.lang = language;
  document.querySelectorAll<HTMLElement>("[data-i18n]").forEach((element) => {
    const value = dictionary[element.dataset.i18n ?? ""];
    if (value !== undefined) element.textContent = value;
  });
  document.querySelectorAll<HTMLElement>("[data-i18n-label]").forEach((element) => {
    const value = dictionary[element.dataset.i18nLabel ?? ""];
    if (value !== undefined) element.setAttribute("aria-label", value);
  });
  const page = document.body.dataset.page;
  if (page && dictionary[`${page}.title`]) document.title = dictionary[`${page}.title`];
  const description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
  if (description && page && dictionary[`${page}.description`]) description.content = dictionary[`${page}.description`];
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
