(() => {
  "use strict";
  const svg = path => `<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
  const icons = {
    idle: svg('<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 3.5V3A1.5 1.5 0 0 0 9 1.5H3A1.5 1.5 0 0 0 1.5 3v6A1.5 1.5 0 0 0 3 10.5h.5"/>'),
    copied: svg('<path d="M3 8.5l3.2 3L13 4.5"/>'),
    failed: svg('<path d="M4 4l8 8M12 4l-8 8"/>')
  };
  const labels = {idle: "복사", copied: "복사됨", failed: "복사 실패"};
  const resetDelay = 2000;

  const live = document.createElement("span");
  live.className = "sr-only";
  live.setAttribute("role", "status");
  live.setAttribute("aria-live", "polite");
  document.body.append(live);
  const announce = message => {
    live.textContent = "";
    window.setTimeout(() => { live.textContent = message; }, 50);
  };

  const selectContents = node => {
    const selection = window.getSelection();
    if (!selection) return;
    const range = document.createRange();
    range.selectNodeContents(node);
    selection.removeAllRanges();
    selection.addRange(range);
  };

  // The async Clipboard API needs a secure context; the textarea fallback covers other cases.
  const writeText = async text => {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return;
      } catch (error) {
        if (error.name !== "NotAllowedError" && error.name !== "SecurityError") throw error;
      }
    }
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;top:0;left:-9999px;opacity:0";
    document.body.append(area);
    area.select();
    try {
      if (!document.execCommand("copy")) throw new Error("The browser rejected the copy command.");
    } finally {
      area.remove();
    }
  };

  const timers = new WeakMap();
  const setState = (button, state) => {
    window.clearTimeout(timers.get(button));
    button.dataset.state = state === "idle" ? "" : state;
    const text = button.querySelector(".copy-text");
    button.querySelector(".copy-icon").innerHTML = icons[state];
    if (text) text.textContent = labels[state];
    if (state !== "idle") timers.set(button, window.setTimeout(() => setState(button, "idle"), resetDelay));
  };

  const copy = async (button, text, label, source) => {
    try {
      await writeText(text);
      setState(button, "copied");
      announce(`${label} 내용을 클립보드에 복사했습니다.`);
    } catch (error) {
      console.warn("클립보드 복사에 실패했습니다.", error);
      setState(button, "failed");
      if (source) selectContents(source);
      announce(`${label} 복사에 실패했습니다. 선택된 내용을 직접 복사하세요.`);
    }
  };

  const buildButton = (className, label, withText) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.innerHTML = `<span class="copy-icon">${icons.idle}</span>${withText ? `<span class="copy-text">${labels.idle}</span>` : ""}`;
    button.setAttribute("aria-label", `${label} 복사`);
    return button;
  };

  document.querySelectorAll("pre").forEach(pre => {
    if (pre.closest(".code-block")) return;
    const label = pre.getAttribute("aria-label") || pre.dataset.label || "코드";
    const block = document.createElement("div");
    block.className = "code-block";
    const bar = document.createElement("div");
    bar.className = "code-toolbar";
    const title = document.createElement("span");
    title.className = "code-label";
    title.textContent = label;
    const button = buildButton("copy-button", label, true);
    button.addEventListener("click", () => { void copy(button, pre.textContent.replace(/\s+$/, ""), label, pre); });
    bar.append(title, button);
    pre.replaceWith(block);
    block.append(bar, pre);
  });

  document.querySelectorAll("code[data-copy]").forEach(code => {
    const value = code.dataset.copy || code.textContent.trim();
    const button = buildButton("copy-inline", value, false);
    button.title = "복사";
    button.addEventListener("click", () => { void copy(button, value, value, null); });
    code.after(button);
  });
  window.__copyReady = true;
})();
