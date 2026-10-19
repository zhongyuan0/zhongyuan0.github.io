/* Search for /readings/search/: loads every reading once and filters in the browser.
   The data file is written by tools/readings/build_page.py. This is the site's only script. */
(function () {
  "use strict";
  var script = document.currentScript;
  var LIMIT = 200;
  var form, q, multi, status, list, data, timer;

  function norm(s) {
    return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[‘’]/g, "'");
  }
  function plain(html) {
    var d = document.createElement("div");
    d.innerHTML = html;
    return d.textContent;
  }

  function render() {
    var terms = norm(q.value).split(/\s+/).filter(Boolean);
    var onlyMulti = multi.checked;
    var params = new URLSearchParams();
    if (q.value.trim()) params.set("q", q.value.trim());
    if (onlyMulti) params.set("multi", "1");
    history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params : ""));
    list.textContent = "";
    if (!terms.length) {
      status.textContent = "Type to search.";
      return;
    }
    var hits = data.items.filter(function (it) {
      if (onlyMulti && it.n < 2) return false;
      for (var i = 0; i < terms.length; i++) if (it.t.indexOf(terms[i]) < 0) return false;
      return true;
    });
    hits.sort(function (a, b) { return b.n - a.n || (a.y || 9999) - (b.y || 9999); });
    var n = hits.length;
    status.textContent = !n ? "No readings match."
      : n > LIMIT ? "Showing the first " + LIMIT + " of " + n.toLocaleString("en") + " readings; add a word to narrow the search."
      : n + (n === 1 ? " reading" : " readings") + ".";
    var html = "";
    hits.slice(0, LIMIT).forEach(function (it) {
      var label = "Listed in " + it.n + " of " + data.sources + " sources";
      html += "<li" + (it.n >= data.core ? ' class="core"' : "") + '><span class="rl-ref">' + it.h +
        ' <span class="rl-where"><a href="' + it.u + '">' + it.l + "</a>" + (it.s ? " · " + it.s : "") + "</span></span>" +
        '<span class="rl-count" title="' + label + '" aria-label="' + label + '">' + it.n + "</span></li>";
    });
    list.innerHTML = html;
  }

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(render, 120);
  }

  document.addEventListener("DOMContentLoaded", function () {
    form = document.querySelector(".rl-search-form");
    q = document.getElementById("rl-q");
    multi = document.getElementById("rl-multi");
    status = document.getElementById("rl-status");
    list = document.getElementById("rl-results");
    var params = new URLSearchParams(location.search);
    q.value = params.get("q") || "";
    multi.checked = params.get("multi") === "1";
    status.textContent = "Loading the readings…";
    fetch(script.getAttribute("data-index"))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        d.items.forEach(function (it) { it.t = norm(plain(it.h)); });
        data = d;
        render();
        q.addEventListener("input", schedule);
        multi.addEventListener("change", render);
        form.addEventListener("submit", function (e) { e.preventDefault(); render(); });
      })
      .catch(function () {
        status.textContent = "The readings could not be loaded. Please reload the page.";
      });
  });
})();
