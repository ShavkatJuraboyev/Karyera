(function () {
  "use strict";

  /* ---------- Yordamchi ---------- */
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  function icon(cls) { return el("i", { "class": "bi " + cls, "aria-hidden": "true" }); }
  var hasDialog = typeof HTMLDialogElement === "function";

  /* ==========================================================================
     Tasdiqlash oynasi (window.confirm o'rniga)
     ========================================================================== */
  var confirmDlg = document.getElementById("confirm-dialog");
  function askConfirm(message, onYes) {
    if (!confirmDlg || !hasDialog) { if (window.confirm(message)) onYes(); return; }
    var danger = /o'chir|bekor|yop|rad et|chiq/i.test(message);
    confirmDlg.querySelector("#cd-text").textContent = message;
    var ok = confirmDlg.querySelector("#cd-ok");
    ok.className = "btn " + (danger ? "btn-danger" : "btn-brand");
    confirmDlg.querySelector(".dlg-icon").classList.toggle("is-info", !danger);
    confirmDlg.returnValue = "";
    var done = function () {
      confirmDlg.removeEventListener("close", done);
      if (confirmDlg.returnValue === "ok") onYes();
    };
    confirmDlg.addEventListener("close", done);
    confirmDlg.showModal();
    ok.focus();
  }
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (f.dataset.confirmed === "1") return;
      e.preventDefault();
      e.stopImmediatePropagation();
      var submitter = e.submitter;
      askConfirm(f.getAttribute("data-confirm"), function () {
        f.dataset.confirmed = "1";
        if (f.requestSubmit) f.requestSubmit(submitter || undefined); else f.submit();
      });
    });
  });

  /* Dialog tashqarisini bosganda yopish */
  document.querySelectorAll("dialog.dlg").forEach(function (d) {
    d.addEventListener("click", function (e) {
      if (e.target === d) d.close("cancel");
    });
  });

  /* ==========================================================================
     Tezkor menyu (Ctrl+K yoki /)
     ========================================================================== */
  var pal = document.getElementById("palette");
  if (pal && hasDialog) {
    var input = document.getElementById("pal-input");
    var list = document.getElementById("pal-list");
    var items = [], active = 0, remote = [], timer = null, lastQuery = "";

    function collectCommands() {
      var seen = {}, out = [];
      var group = "";
      document.querySelectorAll(".sb-nav .sb-title, .sb-nav .sb-link, .site-nav a, .mobile-nav a").forEach(function (n) {
        if (n.classList.contains("sb-title")) { group = n.textContent.trim(); return; }
        var href = n.getAttribute("href");
        if (!href || href === "#" || seen[href]) return;
        seen[href] = true;
        var ic = n.querySelector("i.bi");
        var iconCls = ic ? (ic.className.match(/bi-[\w-]+/) || ["bi-arrow-right"])[0] : "bi-arrow-right";
        out.push({ label: n.textContent.trim(), href: href, icon: iconCls, group: group || "Sahifalar" });
      });
      [["Ish beruvchi bo'lib ro'yxatdan o'tish", "/hisob/royxatdan-otish/ish-beruvchi/", "bi-building-add"],
       ["Parolni o'zgartirish", "/hisob/parol-ozgartirish/", "bi-key"],
       ["Shaxsiy ma'lumotlar", "/hisob/profil/", "bi-person-gear"]].forEach(function (x) {
        if (seen[x[1]]) return;
        var isAuth = !!document.querySelector(".sb-nav");
        if (x[1].indexOf("royxatdan") > -1 && isAuth) return;
        if (x[1].indexOf("parol-ozgartirish") > -1 && !isAuth) return;
        if (x[1].indexOf("/hisob/profil/") > -1 && !isAuth) return;
        out.push({ label: x[0], href: x[1], icon: x[2], group: "Hisob" });
      });
      return out;
    }

    function norm(s) { return (s || "").toLowerCase().replace(/[ʻʼ’‘`]/g, "'"); }

    function render() {
      var q = norm(input.value.trim());
      var cmds = collectCommands().filter(function (c) { return !q || norm(c.label).indexOf(q) > -1 || norm(c.group).indexOf(q) > -1; });
      items = cmds.slice(0, 9);
      if (remote.length) {
        remote.forEach(function (v) { items.push({ label: v.title, sub: v.employer, href: "/vakansiyalar/" + v.id + "/", icon: "bi-briefcase", group: "Vakansiyalar" }); });
      }
      if (q.length >= 1) {
        items.push({ label: "«" + input.value.trim() + "» bo'yicha vakansiya qidirish", href: "/vakansiyalar/?q=" + encodeURIComponent(input.value.trim()), icon: "bi-search", group: "Qidiruv" });
      }
      if (active >= items.length) active = 0;
      list.innerHTML = "";
      if (!items.length) { list.appendChild(el("li", { "class": "pal-empty", text: "Hech narsa topilmadi" })); return; }
      var lastGroup = null;
      items.forEach(function (it, i) {
        if (it.group !== lastGroup) { list.appendChild(el("li", { "class": "pal-group", role: "presentation", text: it.group })); lastGroup = it.group; }
        var li = el("li", { "class": "pal-item" + (i === active ? " active" : ""), role: "option", id: "pal-opt-" + i, "aria-selected": i === active ? "true" : "false" }, [
          icon(it.icon),
          el("span", { "class": "pal-label" }, [el("span", { text: it.label }), it.sub ? el("small", { text: it.sub }) : null])
        ]);
        li.addEventListener("mousemove", function () { if (active !== i) { active = i; paintActive(); } });
        li.addEventListener("click", function () { go(it); });
        list.appendChild(li);
      });
      input.setAttribute("aria-activedescendant", "pal-opt-" + active);
    }
    function paintActive() {
      list.querySelectorAll(".pal-item").forEach(function (n, i) {
        n.classList.toggle("active", i === active); n.setAttribute("aria-selected", i === active ? "true" : "false");
      });
      var a = list.querySelector(".pal-item.active"); if (a) a.scrollIntoView({ block: "nearest" });
      input.setAttribute("aria-activedescendant", "pal-opt-" + active);
    }
    function go(it) { if (it && it.href) window.location.href = it.href; }

    function fetchVacancies(q) {
      if (q.length < 2) { remote = []; render(); return; }
      lastQuery = q;
      fetch("/api/v1/vacancies/?search=" + encodeURIComponent(q), { headers: { "Accept": "application/json" }, credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : { results: [] }; })
        .then(function (d) {
          if (q !== lastQuery) return;
          remote = (d.results || []).slice(0, 5).map(function (v) { return { id: v.id, title: v.title, employer: v.employer ? v.employer.name : "" }; });
          render();
        })
        .catch(function () { remote = []; });
    }

    function openPalette() {
      if (pal.open) return;
      input.value = ""; remote = []; active = 0; render();
      pal.showModal(); input.focus();
    }
    input.addEventListener("input", function () {
      active = 0; render();
      clearTimeout(timer);
      var q = input.value.trim();
      timer = setTimeout(function () { fetchVacancies(q); }, 220);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); active = (active + 1) % Math.max(items.length, 1); paintActive(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); active = (active - 1 + items.length) % Math.max(items.length, 1); paintActive(); }
      else if (e.key === "Enter") { e.preventDefault(); go(items[active]); }
    });
    document.addEventListener("keydown", function (e) {
      var tag = (e.target.tagName || "").toLowerCase();
      var typing = tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); pal.open ? pal.close() : openPalette(); }
      else if (e.key === "/" && !typing && !e.ctrlKey && !e.metaKey) { e.preventDefault(); openPalette(); }
    });
    document.querySelectorAll("[data-palette-open]").forEach(function (b) { b.addEventListener("click", openPalette); });
  }

  /* ==========================================================================
     Parolni ko'rsatish / yashirish
     ========================================================================== */
  document.querySelectorAll("input[type=password]").forEach(function (inp) {
    if (inp.closest(".pw-wrap")) return;
    var wrap = el("div", { "class": "pw-wrap" });
    inp.parentNode.insertBefore(wrap, inp);
    wrap.appendChild(inp);
    var btn = el("button", { type: "button", "class": "pw-toggle", "aria-label": "Parolni ko'rsatish", title: "Parolni ko'rsatish" }, [icon("bi-eye")]);
    btn.addEventListener("click", function () {
      var show = inp.type === "password";
      inp.type = show ? "text" : "password";
      btn.firstChild.className = "bi " + (show ? "bi-eye-slash" : "bi-eye");
      var t = show ? "Parolni yashirish" : "Parolni ko'rsatish";
      btn.setAttribute("aria-label", t); btn.title = t;
    });
    wrap.appendChild(btn);
  });

  /* ==========================================================================
     Fayl yuklash: hajm tekshiruvi va rasmni oldindan ko'rish
     ========================================================================== */
  var MAX = 5 * 1024 * 1024;
  document.querySelectorAll("input[type=file]").forEach(function (inp) {
    var note = el("div", { "class": "file-note", "aria-live": "polite" });
    inp.insertAdjacentElement("afterend", note);
    inp.addEventListener("change", function () {
      note.innerHTML = "";
      note.classList.remove("is-error");
      var f = inp.files && inp.files[0];
      if (!f) return;
      if (f.size > MAX) {
        note.classList.add("is-error");
        note.textContent = "Fayl hajmi 5 MB dan oshmasligi kerak (" + (f.size / 1048576).toFixed(1) + " MB).";
        inp.value = "";
        return;
      }
      if (f.type && f.type.indexOf("image/") === 0) {
        var img = el("img", { "class": "file-thumb", alt: "Tanlangan rasm" });
        img.src = URL.createObjectURL(f);
        img.onload = function () { URL.revokeObjectURL(img.src); };
        note.appendChild(img);
      }
      note.appendChild(el("span", { text: f.name + " (" + (f.size / 1024 < 1024 ? Math.round(f.size / 1024) + " KB" : (f.size / 1048576).toFixed(1) + " MB") + ")" }));
    });
  });

  /* ==========================================================================
     Ko'p tanlovli ro'yxat: qidiruv + belgilash
     ========================================================================== */
  document.querySelectorAll("select[multiple]").forEach(function (sel) {
    if (sel.options.length < 6) return;
    sel.classList.add("visually-hidden");
    sel.setAttribute("tabindex", "-1");
    sel.setAttribute("aria-hidden", "true");
    var box = el("div", { "class": "ms" });
    var search = el("input", { type: "search", "class": "form-control ms-search", placeholder: "Qidirish...", "aria-label": "Ro'yxatdan qidirish", autocomplete: "off" });
    var counter = el("div", { "class": "ms-count", "aria-live": "polite" });
    var listEl = el("div", { "class": "ms-list", role: "group" });
    var rows = [];
    Array.prototype.forEach.call(sel.options, function (o) {
      var id = sel.id + "-ms-" + o.value;
      var cb = el("input", { type: "checkbox", id: id, "class": "form-check-input" });
      cb.checked = o.selected;
      var lab = el("label", { "for": id, "class": "ms-row", text: o.textContent });
      lab.insertBefore(cb, lab.firstChild);
      cb.addEventListener("change", function () { o.selected = cb.checked; update(); });
      listEl.appendChild(lab);
      rows.push({ lab: lab, text: o.textContent.toLowerCase() });
    });
    function update() {
      var n = Array.prototype.filter.call(sel.options, function (o) { return o.selected; }).length;
      counter.textContent = n ? "Tanlangan: " + n + " ta" : "Hech narsa tanlanmagan, barcha yo'nalishlar uchun mos hisoblanadi";
    }
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      rows.forEach(function (r) { r.lab.style.display = !q || r.text.indexOf(q) > -1 ? "" : "none"; });
    });
    search.addEventListener("keydown", function (e) { if (e.key === "Enter") e.preventDefault(); });
    box.appendChild(search); box.appendChild(listEl); box.appendChild(counter);
    sel.parentNode.insertBefore(box, sel);
    update();
  });
})();
