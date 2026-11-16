(function () {
  const dataEl = document.getElementById("speakData");
  let slides = [];
  try {
    slides = JSON.parse(dataEl.textContent);
  } catch (err) {
    slides = [];
  }
  if (!Array.isArray(slides) || !slides.length) {
    slides = [{ title: "空稿", script: "还没有句子。", en: "", zh: "", words: [] }];
  }

  const scriptList = document.getElementById("scriptList");
  const guides = document.getElementById("safeGuides");
  const btnGuide = document.getElementById("btnGuide");
  const cards = slides.map(function (s, i) {
    const card = document.createElement("article");
    card.className = "script-card" + (i === 0 ? " active" : "");
    const idx = document.createElement("p");
    idx.className = "idx";
    idx.textContent = "第 " + (i + 1) + " 页";
    const title = document.createElement("p");
    title.className = "title";
    title.textContent = s.title || ("第 " + (i + 1) + " 页");
    const body = document.createElement("p");
    body.className = "body";
    body.textContent = s.script || "";
    card.appendChild(idx);
    card.appendChild(title);
    card.appendChild(body);
    card.addEventListener("click", function () { go(i); });
    scriptList.appendChild(card);
    return card;
  });

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }
  function highlightEn(en, words) {
    const src = en || "";
    const terms = (words || [])
      .map(function (w) { return ((w && w.text) || w || "").trim(); })
      .filter(Boolean)
      .sort(function (a, b) { return b.length - a.length; });
    if (!terms.length) return escapeHtml(src);
    let out = "";
    let i = 0;
    while (i < src.length) {
      let found = null;
      for (let t = 0; t < terms.length; t++) {
        const term = terms[t];
        const slice = src.slice(i, i + term.length);
        if (slice.toLowerCase() !== term.toLowerCase()) continue;
        const beforeOk = i === 0 || !/[A-Za-z0-9]/.test(src[i - 1]) || !/^[A-Za-z0-9]/.test(term);
        const afterCh = src[i + term.length];
        const afterOk = afterCh == null || !/[A-Za-z0-9]/.test(afterCh) || !/[A-Za-z0-9]$/.test(term);
        if (beforeOk && afterOk) {
          found = slice;
          break;
        }
      }
      if (found) {
        out += '<mark class="vocab">' + escapeHtml(found) + "</mark>";
        i += found.length;
      } else {
        out += escapeHtml(src[i]);
        i += 1;
      }
    }
    return out;
  }

  let index = 0;
  function setActive(i) {
    index = i;
    const s = slides[index] || {};
    const label = document.getElementById("pageLabel");
    if (label) label.textContent = (index + 1) + "/" + slides.length;
    cards.forEach(function (c, j) { c.classList.toggle("active", j === index); });
    const active = cards[index];
    if (active && active.scrollIntoView) {
      active.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    document.getElementById("captionEn").innerHTML = highlightEn(s.en || "", s.words);
    document.getElementById("captionZh").textContent = s.zh || "";
    const attr = document.getElementById("captionAttr");
    attr.textContent = s.attr || "";
    attr.style.display = s.attr ? "" : "none";
    const row = document.getElementById("wordRow");
    row.innerHTML = "";
    (s.words || []).forEach(function (w) {
      const text = (w && w.text) || w || "";
      const meaning = (w && w.meaning) || "";
      if (!text) return;
      const chip = document.createElement("span");
      chip.className = "word-chip";
      chip.innerHTML = '<span class="w">' + escapeHtml(text) + '</span>' +
        (meaning ? '<span class="m">' + escapeHtml(meaning) + "</span>" : "");
      row.appendChild(chip);
    });
  }
  function go(i) {
    i = Math.max(0, Math.min(slides.length - 1, i));
    setActive(i);
  }
  function next() { go(index + 1); }
  function prev() { go(index - 1); }
  document.getElementById("btnNext").addEventListener("click", next);
  document.getElementById("btnPrev").addEventListener("click", prev);
  btnGuide.addEventListener("click", function () {
    guides.classList.toggle("on");
    btnGuide.classList.toggle("on", guides.classList.contains("on"));
  });

  var workbench = document.querySelector(".workbench");
  var btnFlip = document.getElementById("btnFlip");
  var FLIP_KEY = "ting-speak-layout-flip";
  function applyFlip(on) {
    if (!workbench) return;
    workbench.classList.toggle("layout-flip", !!on);
    if (btnFlip) btnFlip.classList.toggle("on", !!on);
    try { localStorage.setItem(FLIP_KEY, on ? "1" : "0"); } catch (err) {}
  }
  function toggleFlip() {
    applyFlip(!(workbench && workbench.classList.contains("layout-flip")));
  }
  if (btnFlip) btnFlip.addEventListener("click", toggleFlip);
  try { if (localStorage.getItem(FLIP_KEY) === "1") applyFlip(true); } catch (err) {}

  window.addEventListener("keydown", function (e) {
    if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
    if (e.key === "ArrowDown" || e.key === "PageDown" || e.key === " " || e.key === "ArrowRight") {
      e.preventDefault();
      next();
    } else if (e.key === "ArrowUp" || e.key === "PageUp" || e.key === "ArrowLeft") {
      e.preventDefault();
      prev();
    } else if (e.key === "g" || e.key === "G") {
      guides.classList.toggle("on");
      btnGuide.classList.toggle("on", guides.classList.contains("on"));
    } else if (e.key === "l" || e.key === "L") {
      e.preventDefault();
      toggleFlip();
    } else if (e.key === "Home") {
      e.preventDefault();
      go(0);
    } else if (e.key === "End") {
      e.preventDefault();
      go(slides.length - 1);
    }
  });

  var start = 0;
  try {
    var params = new URLSearchParams(location.search);
    var q = params.get("page");
    if (q) start = parseInt(q, 10) - 1;
    if (params.get("guides") === "1") {
      guides.classList.add("on");
      if (btnGuide) btnGuide.classList.add("on");
    }
  } catch (err) {}
  go(Number.isFinite(start) ? start : 0);
})();

