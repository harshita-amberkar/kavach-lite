/* Kavach content script: scans the prompt box before it is sent.
   All detection and masking processing runs locally. */
(() => {
  let policy = {}, bypassNextText = null;

  chrome.storage.sync.get("policy", (v) => {
    policy = v.policy || {};
  });

  chrome.storage.onChanged.addListener((c) => {
    if (c.policy) policy = c.policy.newValue || {};
  });

  const EDITABLE =
    'textarea, [contenteditable="true"], [contenteditable=""]';

  const SEND =
    '[data-testid="send-button"], button[aria-label*="send" i], button[type="submit"]';

  const visible = (el) =>
    el && el.getClientRects().length > 0;

  const getEditable = (t) =>
    (t && t.closest && t.closest(EDITABLE)) ||
    (document.activeElement &&
      document.activeElement.closest &&
      document.activeElement.closest(EDITABLE)) ||
    [...document.querySelectorAll(EDITABLE)].filter(visible).pop();

  const getText = (el) =>
    el.tagName === "TEXTAREA" ? el.value : el.innerText;

  function setText(el, text) {
    el.focus();

    if (el.tagName === "TEXTAREA") {
      Object.getOwnPropertyDescriptor(
        HTMLTextAreaElement.prototype,
        "value"
      ).set.call(el, text);

      el.dispatchEvent(
        new Event("input", { bubbles: true })
      );
    } else {
      document.execCommand("selectAll", false);
      document.execCommand("insertText", false, text);
    }
  }

  function toast(msg) {
    const d = document.createElement("div");

    d.textContent = msg;
    d.style.cssText =
      "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#14363a;color:#fff;padding:10px 16px;border-radius:8px;font:15px system-ui;z-index:2147483647";

    document.body.appendChild(d);
    setTimeout(() => d.remove(), 4000);
  }

  function modal(items, action, onMask, onSend) {
    const host = document.createElement("div");

    host.style.cssText =
      "all:initial;position:fixed;inset:0;z-index:2147483647";

    const r = host.attachShadow({ mode: "closed" });

    const counts = {};

    items.forEach((f) => {
      counts[f.type] = (counts[f.type] || 0) + 1;
    });

    r.innerHTML = `
      <style>
        .bd {
          position: fixed;
          inset: 0;
          background: rgba(10,25,27,.55);
          display: flex;
          align-items: center;
          justify-content: center;
          font: 16px/1.5 system-ui;
        }
        .c {
          background: #fbfcfb;
          color: #14363a;
          max-width: 420px;
          width: 90%;
          border-radius: 10px;
          padding: 20px 22px;
        }
        h2 {
          margin: 0 0 6px;
          font-size: 18px;
        }
        ul {
          margin: 10px 0 16px;
          padding-left: 20px;
        }
        button {
          font: 600 14px system-ui;
          padding: 8px 14px;
          border-radius: 6px;
          border: 1px solid #14363a;
          background: #fff;
          color: #14363a;
          cursor: pointer;
          margin-right: 8px;
        }
        button.p {
          background: #14363a;
          color: #fff;
        }
        button:focus-visible {
          outline: 3px solid #f2b134;
        }
      </style>

      <div class="bd">
        <div class="c" role="dialog" aria-modal="true"
             aria-labelledby="t">
          <h2 id="t"></h2>
          <div id="m"></div>
          <ul id="l"></ul>
          <div id="b"></div>
        </div>
      </div>
    `;

    r.getElementById("t").textContent =
      action === "block"
        ? "This prompt is blocked"
        : "Sensitive data found";

    r.getElementById("m").textContent =
      action === "block"
        ? "Your organisation's policy does not allow sending this. Remove the items below."
        : "This prompt contains personal or secret data. Mask it before sending?";

    Object.entries(counts).forEach(([type, count]) => {
      const li = document.createElement("li");
      li.textContent = `${type.replace("_", " ")}: ${count}`;
      r.getElementById("l").appendChild(li);
    });

    const btn = (label, cls, fn) => {
      const b = document.createElement("button");
      b.textContent = label;

      if (cls) b.className = cls;

      b.onclick = () => {
        host.remove();
        if (fn) fn();
      };

      r.getElementById("b").appendChild(b);
      return b;
    };

    const first =
      action === "block"
        ? btn("Close", "p")
        : btn("Mask it", "p", onMask);

    if (action !== "block") {
      btn("Send anyway", "", onSend);
      btn("Cancel", "");
    }

    host.addEventListener("keydown", (e) => {
      if (e.key === "Escape") host.remove();
    });

    document.documentElement.appendChild(host);
    first.focus();
  }

  function guard(e, el) {
    if (!el) return;

    const text = getText(el);

    // Permit one approved submission only if the text
    // has not changed since the user approved it.
    if (bypassNextText !== null) {
      const sameText = text === bypassNextText;
      bypassNextText = null;

      if (sameText) return;
    }

    if (!text || !text.trim()) return;

    const { action, items } = Kavach.decide(
      Kavach.scan(text),
      policy
    );

    if (action === "allow") return;

    e.preventDefault();
    e.stopImmediatePropagation();

    const doMask = () => {
      setText(el, Kavach.mask(text, items));
      toast(
        `Masked ${items.length} item(s). Press send when ready.`
      );
    };

    if (action === "mask") return doMask();

    modal(items, action, doMask, () => {
      // Remember the exact prompt the user approved.
      bypassNextText = getText(el);

      const sendButton = [
        ...document.querySelectorAll(SEND)
      ].find(visible);

      if (sendButton) {
        sendButton.click();
      } else {
        toast("Allowed once. Press send again.");
      }
    });
  }

  document.addEventListener("keydown", (e) => {
    if (
      e.key !== "Enter" ||
      e.shiftKey ||
      e.isComposing ||
      !e.target.closest ||
      !e.target.closest(EDITABLE)
    ) {
      return;
    }

    guard(e, getEditable(e.target));
  }, true);

  document.addEventListener("click", (e) => {
    const b = e.target.closest && e.target.closest("button");

    if (!b || !b.matches(SEND)) return;

    guard(e, getEditable(null));
  }, true);
})();