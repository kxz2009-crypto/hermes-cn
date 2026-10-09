"use strict";
const panel = document.getElementById("assistant-panel");
const launch = document.getElementById("assistant-launch");
let previousFocus = null;
let modalMode = false;

function openAssistant() {
  if (!panel || panel.open) return;
  previousFocus = document.activeElement;
  modalMode = window.innerWidth < 1280;
  if (modalMode) panel.showModal();
  else {
    panel.show();
    document.body.classList.add("assistant-open");
  }
  launch.hidden = true;
  document.getElementById("assistant-close").focus();
}
function closeAssistant() {
  if (panel && panel.open) panel.close();
}
if (panel) {
  launch.addEventListener("click", openAssistant);
  document.getElementById("assistant-close").addEventListener("click", closeAssistant);
  document.querySelectorAll("[data-open-assistant]").forEach(button =>
    button.addEventListener("click", openAssistant));
  panel.addEventListener("close", () => {
    document.body.classList.remove("assistant-open");
    launch.hidden = false;
    if (previousFocus && previousFocus.isConnected) previousFocus.focus();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && panel.open) closeAssistant();
  });
  window.addEventListener("resize", () => {
    if (panel.open && modalMode !== (window.innerWidth < 1280)) {
      closeAssistant();
      openAssistant();
    }
  });
}

document.querySelectorAll(".guide pre").forEach(pre => {
  const code = pre.querySelector("code");
  if (!code) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "code-copy";
  button.textContent = "复制命令";
  button.setAttribute("aria-label", "复制此代码块");
  button.addEventListener("click", async () => {
    try {
      if (!navigator.clipboard) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(code.textContent);
      button.textContent = "已复制";
    } catch {
      button.textContent = "复制未成功，请手动选择代码";
    }
    setTimeout(() => button.textContent = "复制命令", 3000);
  });
  pre.append(button);
});
