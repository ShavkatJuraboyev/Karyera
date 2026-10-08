(function () {
  "use strict";

  /* ---------- Mavzu (yorug' / qorong'i) ---------- */
  var root = document.documentElement;
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* xotira yopiq bo'lsa ham ishlaydi */ }
      document.dispatchEvent(new CustomEvent("themechange", { detail: next }));
    });
  });

  /* ---------- Xabarlar (toast): o'zi yopiladi, qo'lda ham yopiladi ---------- */
  function dismiss(el) {
    if (!el || el.classList.contains("leaving")) return;
    el.classList.add("leaving");
    setTimeout(function () { el.remove(); }, 200);
  }
  document.querySelectorAll(".toast-lite").forEach(function (el, i) {
    var closer = el.querySelector("[data-toast-close]");
    if (closer) closer.addEventListener("click", function () { dismiss(el); });
    var long = el.classList.contains("error") || el.classList.contains("warning");
    setTimeout(function () { dismiss(el); }, (long ? 9000 : 5500) + i * 600);
  });

  /* ---------- Fakultet tanlanganda yo'nalishlar ro'yxatini yangilash ---------- */
  function bindDependent(select) {
    var target = document.getElementById(select.getAttribute("data-dependent-target"));
    if (!target) return;
    var url = target.getAttribute("data-faculty-url");
    select.addEventListener("change", function () {
      var current = target.value;
      target.innerHTML = '<option value="">---------</option>';
      if (!select.value) return;
      fetch(url + "?faculty=" + encodeURIComponent(select.value), { headers: { "Accept": "application/json" } })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          data.results.forEach(function (d) {
            var opt = document.createElement("option");
            opt.value = d.id;
            opt.textContent = d.name;
            if (String(d.id) === String(current)) opt.selected = true;
            target.appendChild(opt);
          });
        })
        .catch(function () { /* tarmoq xatosi: ro'yxat bo'sh qoladi */ });
    });
    if (select.value && !target.value) { select.dispatchEvent(new Event("change")); }
  }
  document.querySelectorAll("select[data-dependent-target]").forEach(bindDependent);

  /* ---------- Shartli maydonlar ---------- */
  function fieldBox(el) { return el ? (el.closest(".field") || el.closest(".mb-3, .col-md-6, .col-12")) : null; }
  function show(el, visible) { var b = fieldBox(el); if (b) b.style.display = visible ? "" : "none"; }

  var role = document.getElementById("id_role");
  var course = document.getElementById("id_course");
  var year = document.getElementById("id_graduation_year");
  function toggleRole() {
    if (!role || !course || !year) return;
    var isGrad = role.value === "graduate";
    show(course, !isGrad);
    show(year, isGrad);
  }
  if (role) { role.addEventListener("change", toggleRole); toggleRole(); }

  var status = document.getElementById("id_employment_status");
  function toggleEmployment() {
    if (!status) return;
    var on = status.value === "employed" || status.value === "self_employed";
    ["id_employer_name", "id_position", "id_employed_date"].forEach(function (id) { show(document.getElementById(id), on); });
  }
  if (status) { status.addEventListener("change", toggleEmployment); toggleEmployment(); }

  /* ---------- Tasdiqlash va ikki marta bosishdan himoya ---------- */
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!window.confirm(f.getAttribute("data-confirm"))) e.preventDefault();
    });
  });
  document.querySelectorAll("form").forEach(function (f) {
    if (f.hasAttribute("data-no-lock") || (f.method || "").toLowerCase() === "get") return;
    f.addEventListener("submit", function (e) {
      if (e.defaultPrevented) return;
      var submitter = e.submitter;
      setTimeout(function () {
        f.querySelectorAll("button[type=submit], input[type=submit]").forEach(function (b) {
          b.disabled = true;
          if (b === submitter && b.tagName === "BUTTON" && !b.classList.contains("icon-btn") && !b.classList.contains("btn-link")) {
            b.classList.add("is-loading");
            b.insertAdjacentHTML("afterbegin", '<span class="spinner-border" aria-hidden="true"></span>');
          }
        });
      }, 0);
    });
  });
  window.addEventListener("pageshow", function (e) {
    if (!e.persisted) return;
    document.querySelectorAll("button.is-loading").forEach(function (b) {
      b.classList.remove("is-loading");
      var s = b.querySelector(".spinner-border"); if (s) s.remove();
    });
    document.querySelectorAll("button[disabled][type=submit]").forEach(function (b) { b.disabled = false; });
  });

  /* ---------- Telefon maydoni: faqat raqam, bo'shliq va + ---------- */
  document.querySelectorAll("input[name=phone], input[name=contact_phone], input[name=org_phone]").forEach(function (i) {
    i.setAttribute("inputmode", "tel");
    i.setAttribute("autocomplete", "tel");
  });

  /* ---------- Mobil menyu: havola bosilganda yopiladi ---------- */
  var sidebar = document.getElementById("sidebar");
  if (sidebar && window.bootstrap) {
    sidebar.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        var inst = window.bootstrap.Offcanvas.getInstance(sidebar);
        if (inst) inst.hide();
      });
    });
  }
})();
