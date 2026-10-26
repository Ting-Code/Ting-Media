(function(){
  const deck = document.getElementById('deck');
  const slides = Array.from(deck.querySelectorAll('.slide'));
  const pageNum = document.getElementById('pageNum');
  const pageTotal = document.getElementById('pageTotal');
  const guides = document.getElementById('safeGuides');
  pageTotal.textContent = String(slides.length);
  let index = 0;
  function go(i, smooth){
    index = Math.max(0, Math.min(slides.length - 1, i));
    slides[index].scrollIntoView({behavior: smooth === false ? 'auto' : 'smooth', block: 'start'});
    pageNum.textContent = String(index + 1);
  }
  function next(){ go(index + 1); }
  function prev(){ go(index - 1); }
  document.getElementById('btnNext').addEventListener('click', next);
  document.getElementById('btnPrev').addEventListener('click', prev);
  document.getElementById('btnGuide').addEventListener('click', function(){ guides.classList.toggle('on'); });
  window.addEventListener('keydown', function(e){
    if (e.key === 'ArrowDown' || e.key === 'PageDown' || e.key === ' ' || e.key === 'ArrowRight'){ e.preventDefault(); next(); }
    else if (e.key === 'ArrowUp' || e.key === 'PageUp' || e.key === 'ArrowLeft'){ e.preventDefault(); prev(); }
    else if (e.key === 'g' || e.key === 'G'){ guides.classList.toggle('on'); }
    else if (e.key === 'Home'){ e.preventDefault(); go(0); }
    else if (e.key === 'End'){ e.preventDefault(); go(slides.length - 1); }
  });
  let t = null;
  deck.addEventListener('scroll', function(){
    if (t) clearTimeout(t);
    t = setTimeout(function(){
      const top = deck.scrollTop;
      let best = 0, bestDist = Infinity;
      slides.forEach(function(s, i){
        const d = Math.abs(s.offsetTop - top);
        if (d < bestDist){ bestDist = d; best = i; }
      });
      index = best;
      pageNum.textContent = String(index + 1);
      try {
        const plots = slides[index].querySelectorAll('.js-plotly-plot');
        plots.forEach(function(p){ if (window.Plotly) Plotly.Plots.resize(p); });
      } catch (err) {}
    }, 80);
  });
  go(0, false);
})();