(() => {
  "use strict";
  const storageKey = "internal-guest-guide-theme";
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  let preference = null;

  const reportStorageError = error => {
    if (!(error instanceof DOMException) || !["SecurityError", "QuotaExceededError"].includes(error.name)) {
      throw error;
    }
    console.warn("테마 설정 저장소를 사용할 수 없습니다.", error);
  };

  try {
    preference = window.localStorage.getItem(storageKey);
  } catch (error) {
    reportStorageError(error);
  }
  if (preference !== null && preference !== "light" && preference !== "dark") {
    console.warn("저장된 테마 설정이 잘못되어 시스템 설정을 사용합니다.");
    preference = null;
  }

  const applyTheme = () => {
    const theme = preference || (systemTheme.matches ? "dark" : "light");
    document.documentElement.dataset.theme = theme;
    const button = document.getElementById("theme-toggle");
    if (button) {
      button.setAttribute("aria-pressed", String(theme === "dark"));
      button.title = theme === "dark" ? "라이트 테마로 전환" : "다크 테마로 전환";
    }
  };
  applyTheme();
  systemTheme.addEventListener("change", () => {
    if (preference === null) applyTheme();
  });

  document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("theme-toggle");
    const status = document.getElementById("theme-status");
    if (!button || !status) throw new Error("Missing theme controls.");
    applyTheme();
    button.addEventListener("click", () => {
      preference = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      applyTheme();
      status.textContent = preference === "dark" ? "다크 테마를 사용합니다." : "라이트 테마를 사용합니다.";
      try {
        window.localStorage.setItem(storageKey, preference);
      } catch (error) {
        reportStorageError(error);
        button.title = "현재 페이지의 테마만 변경했습니다. 설정을 저장하지 못했습니다.";
        status.textContent += " 이 브라우저에서는 설정을 저장하지 못했습니다.";
      }
    });
  }, {once: true});
})();
