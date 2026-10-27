(function () {
  const deck = document.getElementById("deck");
  const slides = Array.from(deck.querySelectorAll(".slide"));
  const guides = document.getElementById("safeGuides");
  const scriptList = document.getElementById("scriptList");
  const btnGuide = document.getElementById("btnGuide");

  const cards = slides.map(function (s, i) {
    const card = document.createElement("article");
    card.className = "script-card" + (i === 0 ? " active" : "");
    const idx = document.createElement("p");
    idx.className = "idx";
    idx.textContent = "\u7b2c " + (i + 1) + " \u9875";
    const title = document.createElement("p");
    title.className = "title";
    title.textContent = s.dataset.title || ("\u7b2c " + (i + 1) + " \u9875");
    const body = document.createElement("p");
    body.className = "body";
    body.textContent = (s.dataset.script || "").replace(/&#10;/g, "\n");
    card.appendChild(idx);
    card.appendChild(title);
    card.appendChild(body);
    card.addEventListener("click", function () { go(i); });
    scriptList.appendChild(card);
    return card;
  });

  function fitPlots(slide) {
    if (!slide || !window.Plotly) return;
    const box = slide.querySelector(".chart-box");
    if (!box) return;
    const w = Math.max(100, Math.floor(box.clientWidth));
    const h = Math.max(140, Math.floor(box.clientHeight));
    box.querySelectorAll(".js-plotly-plot").forEach(function (p) {
      try {
        Plotly.relayout(p, { width: w, height: h, autosize: false });
      } catch (err) {}
    });
  }

  let index = 0;
  function setActive(i) {
    index = i;
    const label = document.getElementById("pageLabel");
    if (label) label.textContent = (index + 1) + "/" + slides.length;
    cards.forEach(function (c, j) { c.classList.toggle("active", j === index); });
    const active = cards[index];
    if (active && active.scrollIntoView) {
      active.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    fitPlots(slides[index]);
  }
  function go(i, smooth) {
    i = Math.max(0, Math.min(slides.length - 1, i));
    slides[i].scrollIntoView({
      behavior: smooth === false ? "auto" : "smooth",
      block: "start",
    });
    setActive(i);
    requestAnimationFrame(function () {
      fitPlots(slides[i]);
      setTimeout(function () { fitPlots(slides[i]); }, 80);
    });
  }
  function next() { go(index + 1); }
  function prev() { go(index - 1); }
  document.getElementById("btnNext").addEventListener("click", next);
  document.getElementById("btnPrev").addEventListener("click", prev);
  btnGuide.addEventListener("click", function () {
    guides.classList.toggle("on");
    btnGuide.classList.toggle("on", guides.classList.contains("on"));
  });
  window.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown" || e.key === "PageDown" || e.key === " " || e.key === "ArrowRight") {
      e.preventDefault();
      next();
    } else if (e.key === "ArrowUp" || e.key === "PageUp" || e.key === "ArrowLeft") {
      e.preventDefault();
      prev();
    } else if (e.key === "g" || e.key === "G") {
      guides.classList.toggle("on");
      btnGuide.classList.toggle("on", guides.classList.contains("on"));
    } else if (e.key === "Home") {
      e.preventDefault();
      go(0);
    } else if (e.key === "End") {
      e.preventDefault();
      go(slides.length - 1);
    }
  });
  let t = null;
  deck.addEventListener("scroll", function () {
    if (t) clearTimeout(t);
    t = setTimeout(function () {
      const top = deck.scrollTop;
      let best = 0, bestDist = Infinity;
      slides.forEach(function (s, i) {
        const d = Math.abs(s.offsetTop - top);
        if (d < bestDist) {
          bestDist = d;
          best = i;
        }
      });
      setActive(best);
    }, 80);
  });
  window.addEventListener("resize", function () {
    fitPlots(slides[index]);
  });
  go(0, false);
})();
