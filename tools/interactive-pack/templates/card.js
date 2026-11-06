(function () {
  var data = window.__PACK_DATA__ || { title: "", sections: [] };
  var app = document.getElementById("app");
  var dots = document.getElementById("dots");
  var pages = [];
  var idx = 0;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null && text !== "") n.textContent = text;
    return n;
  }

  function render() {
    app.innerHTML = "";
    dots.innerHTML = "";
    pages = [];
    var sections = data.sections || [];
    if (!sections.length) {
      sections = [{ heading: "暂无内容", body: "请重新生成数据包", items: [] }];
    }
    for (var i = 0; i < sections.length; i++) {
      var sec = sections[i];
      var page = el("section", "page" + (i === 0 ? " active" : ""));
      var card = el("article", "card");
      card.appendChild(el("h2", null, sec.heading || ("板块 " + (i + 1))));
      if (sec.body) card.appendChild(el("p", "body", sec.body));
      var items = sec.items || [];
      for (var j = 0; j < items.length; j++) {
        (function (it) {
          var row = el("div", "item collapsed");
          row.appendChild(el("div", "t", it.title || it.text || ""));
          if (it.meta) row.appendChild(el("div", "m", it.meta));
          if (it.text && it.title) row.appendChild(el("div", "x", it.text));
          var btn = el("button", "btn", "展开");
          btn.type = "button";
          btn.addEventListener("click", function () {
            var open = row.className.indexOf("collapsed") === -1;
            row.className = open ? "item collapsed" : "item";
            btn.textContent = open ? "展开" : "收起";
          });
          if (it.text && it.title) row.appendChild(btn);
          card.appendChild(row);
        })(items[j]);
      }
      page.appendChild(card);
      app.appendChild(page);
      pages.push(page);
      var d = el("span", "dot" + (i === 0 ? " on" : ""));
      dots.appendChild(d);
    }
  }

  function go(n) {
    if (n < 0 || n >= pages.length || n === idx) return;
    pages[idx].className = "page" + (n > idx ? " prev" : "");
    pages[n].className = "page active";
    var ds = dots.children;
    if (ds[idx]) ds[idx].className = "dot";
    if (ds[n]) ds[n].className = "dot on";
    idx = n;
  }

  var startX = 0, startY = 0, locked = null;
  app.addEventListener("touchstart", function (e) {
    if (!e.touches || !e.touches.length) return;
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    locked = null;
  }, { passive: true });
  app.addEventListener("touchmove", function (e) {
    if (!e.touches || !e.touches.length) return;
    var dx = e.touches[0].clientX - startX;
    var dy = e.touches[0].clientY - startY;
    if (locked === null) locked = Math.abs(dx) > Math.abs(dy);
  }, { passive: true });
  app.addEventListener("touchend", function (e) {
    var t = e.changedTouches && e.changedTouches[0];
    if (!t) return;
    var dx = t.clientX - startX;
    if (locked && Math.abs(dx) > 48) go(idx + (dx < 0 ? 1 : -1));
  }, { passive: true });

  document.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight" || e.key === "PageDown") go(idx + 1);
    if (e.key === "ArrowLeft" || e.key === "PageUp") go(idx - 1);
  });

  render();
})();
