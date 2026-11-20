(function () {
  "use strict";

  var course = window.__ENGLISH_PACK_COURSE__;
  if (!course || !Array.isArray(course.sentences) || !course.sentences.length) {
    document.body.innerHTML = "<p style='padding:24px'>课程数据缺失，请重新生成练习页。</p>";
    return;
  }

  var PREFS_KEY = "ting-tools.english-pack.prefs";
  var progressKey = "ting-tools.english-pack.progress." + course.id;
  var hasSpeech = typeof window.speechSynthesis === "object" && window.speechSynthesis !== null;
  var SpeechUtterance = window.SpeechSynthesisUtterance;

  var state = {
    index: 0,
    mastered: {},
    hidden: false,
    looping: false,
    rate: 1,
    voiceURI: "",
    speaking: false
  };

  var els = {
    title: document.getElementById("course-title"),
    subtitle: document.getElementById("course-subtitle"),
    progress: document.getElementById("progress-line"),
    list: document.getElementById("sentence-list"),
    banner: document.getElementById("status-banner"),
    label: document.getElementById("sentence-label"),
    note: document.getElementById("sentence-note"),
    block: document.getElementById("subtitle-block"),
    en: document.getElementById("sentence-en"),
    zh: document.getElementById("sentence-zh"),
    recall: document.getElementById("recall-hint"),
    vocab: document.getElementById("vocab-list"),
    play: document.getElementById("btn-play"),
    loop: document.getElementById("btn-loop"),
    rate: document.getElementById("rate-range"),
    rateValue: document.getElementById("rate-value"),
    voice: document.getElementById("voice-select"),
    subs: document.getElementById("btn-subs"),
    retry: document.getElementById("btn-retry"),
    master: document.getElementById("btn-master"),
    prev: document.getElementById("btn-prev"),
    next: document.getElementById("btn-next"),
    done: document.getElementById("done-banner")
  };

  var currentAudio = null;
  var currentUtterance = null;
  var loopTimer = 0;
  var storageOk = true;

  function showBanner(text, isError) {
    if (!text) {
      els.banner.hidden = true;
      els.banner.textContent = "";
      return;
    }
    els.banner.hidden = false;
    els.banner.textContent = text;
    els.banner.style.background = isError ? "var(--danger-soft)" : "var(--warn-soft)";
    els.banner.style.color = isError ? "#8a2f24" : "var(--warn)";
  }

  function readJson(key, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      if (!raw) return fallback;
      var data = JSON.parse(raw);
      return data && typeof data === "object" ? data : fallback;
    } catch (err) {
      storageOk = false;
      return fallback;
    }
  }

  function writeJson(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (err) {
      storageOk = false;
    }
  }

  function loadState() {
    var prefs = readJson(PREFS_KEY, {});
    if (typeof prefs.rate === "number" && prefs.rate >= 0.7 && prefs.rate <= 1.15) {
      state.rate = prefs.rate;
    }
    if (typeof prefs.voiceURI === "string") state.voiceURI = prefs.voiceURI;
    if (prefs.looping) state.looping = true;

    var progress = readJson(progressKey, {});
    if (Array.isArray(progress.mastered)) {
      progress.mastered.forEach(function (id) { state.mastered[id] = true; });
    }
    if (progress.currentId) {
      var found = course.sentences.findIndex(function (item) { return item.id === progress.currentId; });
      if (found >= 0) state.index = found;
    }
  }

  function savePrefs() {
    writeJson(PREFS_KEY, {
      rate: state.rate,
      voiceURI: state.voiceURI,
      looping: state.looping
    });
  }

  function saveProgress() {
    writeJson(progressKey, {
      currentId: currentSentence().id,
      mastered: Object.keys(state.mastered).filter(function (id) { return state.mastered[id]; }),
      updatedAt: new Date().toISOString()
    });
  }

  function currentSentence() {
    return course.sentences[state.index];
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeRe(text) {
    return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function markEnglish(en, words) {
    var source = en || "";
    var items = (words || [])
      .filter(function (word) { return word && word.text; })
      .slice()
      .sort(function (a, b) { return b.text.length - a.text.length; });
    var ranges = [];
    items.forEach(function (word) {
      var re = new RegExp(escapeRe(word.text), "ig");
      var match;
      while ((match = re.exec(source)) !== null) {
        var start = match.index;
        var end = start + match[0].length;
        var overlap = ranges.some(function (range) {
          return !(end <= range.start || start >= range.end);
        });
        if (!overlap) {
          ranges.push({ start: start, end: end, text: match[0] });
        }
      }
    });
    ranges.sort(function (a, b) { return a.start - b.start; });
    var html = "";
    var cursor = 0;
    ranges.forEach(function (range) {
      html += escapeHtml(source.slice(cursor, range.start));
      html += "<mark>" + escapeHtml(range.text) + "</mark>";
      cursor = range.end;
    });
    html += escapeHtml(source.slice(cursor));
    return html;
  }

  function masteredCount() {
    return course.sentences.filter(function (item) { return state.mastered[item.id]; }).length;
  }

  function renderList() {
    els.list.innerHTML = "";
    course.sentences.forEach(function (item, index) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      if (index === state.index) btn.setAttribute("aria-current", "true");
      if (state.mastered[item.id]) btn.classList.add("is-mastered");
      btn.innerHTML = '<span class="dot" aria-hidden="true"></span><p class="en-preview" lang="en"></p>';
      btn.querySelector(".en-preview").textContent = item.en;
      btn.addEventListener("click", function () { goTo(index); });
      li.appendChild(btn);
      els.list.appendChild(li);
    });
  }

  function renderSentence() {
    var item = currentSentence();
    var total = course.sentences.length;
    els.title.textContent = course.title;
    els.subtitle.textContent = course.subtitle || "";
    els.progress.textContent = "已掌握 " + masteredCount() + " / " + total;
    els.label.textContent = "第 " + (state.index + 1) + " 句";
    els.note.textContent = item.note || "";
    els.en.innerHTML = markEnglish(item.en, item.words);
    els.zh.textContent = item.zh || "";
    els.block.hidden = state.hidden;
    els.recall.hidden = !state.hidden;
    els.subs.setAttribute("aria-pressed", state.hidden ? "true" : "false");
    els.subs.textContent = state.hidden ? "显示字幕" : "隐藏字幕";
    els.loop.setAttribute("aria-pressed", state.looping ? "true" : "false");
    els.rate.value = String(state.rate);
    els.rateValue.textContent = Number(state.rate).toFixed(2) + "×";
    els.prev.disabled = state.index <= 0;
    els.next.disabled = state.index >= total - 1;
    els.master.textContent = state.mastered[item.id] ? "已会（可再点）" : "会了";

    els.vocab.innerHTML = "";
    (item.words || []).forEach(function (word) {
      var li = document.createElement("li");
      li.innerHTML = '<span class="term" lang="en"></span><span class="meaning"></span>';
      li.querySelector(".term").textContent = word.text;
      li.querySelector(".meaning").textContent = word.meaning || "";
      els.vocab.appendChild(li);
    });
    els.vocab.hidden = state.hidden || !(item.words && item.words.length);

    els.done.hidden = masteredCount() !== total;
    renderList();
  }

  function englishVoices() {
    if (!hasSpeech) return [];
    return window.speechSynthesis.getVoices().filter(function (voice) {
      return /^en([-_]|$)/i.test(voice.lang || "");
    });
  }

  function selectedVoice() {
    var voices = englishVoices();
    if (!voices.length) return null;
    return voices.find(function (voice) { return voice.voiceURI === state.voiceURI; }) || voices[0];
  }

  function fillVoices() {
    var voices = englishVoices();
    els.voice.innerHTML = "";
    if (!hasSpeech) {
      var missing = document.createElement("option");
      missing.value = "";
      missing.textContent = "当前浏览器不支持语音合成";
      els.voice.appendChild(missing);
      els.voice.disabled = true;
      els.play.disabled = true;
      els.loop.disabled = true;
      showBanner("当前浏览器不支持语音合成。你可以查看字幕并自行跟读，播放和循环按钮已禁用。", true);
      return;
    }
    if (!voices.length) {
      var empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "未检测到英语语音";
      els.voice.appendChild(empty);
      els.voice.disabled = true;
      showBanner("已检测到语音合成，但当前没有可用的英语语音。请在系统或浏览器中安装英语语音包后刷新本页。你仍可先看字幕跟读；若点击播放，将使用系统默认语音，发音可能不是英语。", false);
      return;
    }
    els.voice.disabled = false;
    voices.forEach(function (voice) {
      var opt = document.createElement("option");
      opt.value = voice.voiceURI;
      opt.textContent = (voice.name || "English") + "（" + voice.lang + "）";
      els.voice.appendChild(opt);
    });
    var chosen = selectedVoice();
    if (chosen) {
      state.voiceURI = chosen.voiceURI;
      els.voice.value = chosen.voiceURI;
    }
    showBanner("");
    if (!storageOk) {
      showBanner("当前浏览器无法写入本地进度（localStorage）。本次练习进度仅保留在这个标签页里。", false);
    }
  }

  function stopPlayback() {
    state.speaking = false;
    if (loopTimer) {
      window.clearTimeout(loopTimer);
      loopTimer = 0;
    }
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.removeAttribute("src");
      currentAudio = null;
    }
    currentUtterance = null;
    if (hasSpeech) {
      window.speechSynthesis.cancel();
    }
    els.play.textContent = "播放原句";
  }

  function afterPlay() {
    state.speaking = false;
    currentUtterance = null;
    currentAudio = null;
    els.play.textContent = "播放原句";
    if (state.looping) {
      loopTimer = window.setTimeout(function () {
        if (state.looping) playCurrent();
      }, 450);
    }
  }

  function speakWithTts(text) {
    if (!hasSpeech || typeof SpeechUtterance !== "function") {
      showBanner("当前浏览器不支持语音合成，无法播放原句。", true);
      return;
    }
    var utter = new SpeechUtterance(text);
    utter.rate = state.rate;
    utter.lang = "en-US";
    var voice = selectedVoice();
    if (voice) {
      utter.voice = voice;
      utter.lang = voice.lang || "en-US";
    }
    utter.onend = function () {
      if (currentUtterance === utter) afterPlay();
    };
    utter.onerror = function () {
      if (currentUtterance === utter) {
        stopPlayback();
        showBanner("语音播放失败。请检查系统英语语音包，或换一个浏览器再试。", true);
      }
    };
    currentUtterance = utter;
    state.speaking = true;
    els.play.textContent = "停止播放";
    window.speechSynthesis.speak(utter);
  }

  function playCurrent() {
    var item = currentSentence();
    if (state.speaking) {
      stopPlayback();
      return;
    }
    stopPlayback();
    if (item.audio) {
      var audio = new Audio(item.audio);
      audio.preload = "auto";
      try { audio.playbackRate = state.rate; } catch (err) {}
      currentAudio = audio;
      state.speaking = true;
      els.play.textContent = "停止播放";
      audio.addEventListener("ended", function () {
        if (currentAudio === audio) afterPlay();
      });
      audio.addEventListener("error", function () {
        if (currentAudio === audio) {
          stopPlayback();
          speakWithTts(item.en);
        }
      });
      var playPromise = audio.play();
      if (playPromise && typeof playPromise.then === "function") {
        playPromise.catch(function () {
          stopPlayback();
          speakWithTts(item.en);
        });
      }
      return;
    }
    speakWithTts(item.en);
  }

  function goTo(index) {
    if (index < 0 || index >= course.sentences.length) return;
    stopPlayback();
    state.index = index;
    saveProgress();
    renderSentence();
  }

  function toggleMastered() {
    var id = currentSentence().id;
    if (state.mastered[id]) {
      delete state.mastered[id];
      saveProgress();
      renderSentence();
      return;
    }
    state.mastered[id] = true;
    saveProgress();
    var nextUnmastered = course.sentences.findIndex(function (item, i) {
      return i > state.index && !state.mastered[item.id];
    });
    if (nextUnmastered < 0) {
      nextUnmastered = course.sentences.findIndex(function (item) {
        return !state.mastered[item.id];
      });
    }
    if (nextUnmastered >= 0) {
      goTo(nextUnmastered);
    } else {
      renderSentence();
    }
  }

  function retryCurrent() {
    var id = currentSentence().id;
    if (state.mastered[id]) delete state.mastered[id];
    saveProgress();
    renderSentence();
    if (hasSpeech) playCurrent();
  }

  els.play.addEventListener("click", playCurrent);
  els.loop.addEventListener("click", function () {
    state.looping = !state.looping;
    savePrefs();
    renderSentence();
    if (!state.looping) {
      if (loopTimer) {
        window.clearTimeout(loopTimer);
        loopTimer = 0;
      }
    }
  });
  els.rate.addEventListener("input", function () {
    state.rate = Number(els.rate.value);
    if (currentAudio) {
      try { currentAudio.playbackRate = state.rate; } catch (err) {}
    }
    els.rateValue.textContent = state.rate.toFixed(2) + "×";
    savePrefs();
  });
  els.voice.addEventListener("change", function () {
    state.voiceURI = els.voice.value;
    savePrefs();
  });
  els.subs.addEventListener("click", function () {
    state.hidden = !state.hidden;
    renderSentence();
  });
  els.retry.addEventListener("click", retryCurrent);
  els.master.addEventListener("click", toggleMastered);
  els.prev.addEventListener("click", function () { goTo(state.index - 1); });
  els.next.addEventListener("click", function () { goTo(state.index + 1); });

  document.addEventListener("keydown", function (event) {
    var tag = (event.target && event.target.tagName) || "";
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
    if (event.code === "Space") {
      event.preventDefault();
      playCurrent();
    } else if (event.key === "ArrowLeft") {
      goTo(state.index - 1);
    } else if (event.key === "ArrowRight") {
      goTo(state.index + 1);
    } else if (event.key === "h" || event.key === "H") {
      state.hidden = !state.hidden;
      renderSentence();
    }
  });

  loadState();
  els.title.textContent = course.title;
  fillVoices();
  if (hasSpeech) {
    window.speechSynthesis.addEventListener("voiceschanged", fillVoices);
    window.setTimeout(fillVoices, 300);
  }
  renderSentence();
  if (!storageOk) {
    showBanner("当前浏览器无法写入本地进度（localStorage）。本次练习进度仅保留在这个标签页里。", false);
  }
})();
