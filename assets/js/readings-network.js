/* /readings/network/: click or focus a reading to highlight its links and show what it is assigned with.
   The data is in the page (script#nw-data), written by tools/readings/build_page.py. */
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var data = JSON.parse(document.getElementById("nw-data").textContent);
    var svg = document.querySelector("svg.nw");
    var panel = document.getElementById("nw-panel");
    var sel = document.getElementById("nw-sel");
    var list = document.getElementById("nw-nb");
    var nodes = {}, edges = [];
    svg.querySelectorAll(".nw-n").forEach(function (c) { nodes[c.dataset.i] = c; });
    svg.querySelectorAll(".nw-e").forEach(function (l) { edges.push(l); });
    var current = null;

    function clear() {
      svg.classList.remove("has-sel");
      svg.querySelectorAll(".sel, .nb, .on").forEach(function (el) { el.classList.remove("sel", "nb", "on"); });
      current = null;
      panel.hidden = true;
    }

    function select(i) {
      if (current === i) { clear(); return; }
      clear();
      var d = data[i];
      if (!d) return;
      current = i;
      svg.classList.add("has-sel");
      nodes[i].classList.add("sel");
      var near = {};
      d.nb.forEach(function (p) { near[p[0]] = p[1]; });
      edges.forEach(function (l) {
        if (l.dataset.a === i || l.dataset.b === i) {
          l.classList.add("on");
          near[l.dataset.a === i ? l.dataset.b : l.dataset.a] = near[l.dataset.a === i ? l.dataset.b : l.dataset.a] || 1;
        }
      });
      Object.keys(near).forEach(function (j) { if (nodes[j]) nodes[j].classList.add("nb"); });
      sel.innerHTML = '<span class="rl-ref">' + d.h + ' <span class="rl-where"><a href="' + d.u + '">' + d.st + '</a> · in ' + d.n + " sources</span></span>";
      list.innerHTML = d.nb.map(function (p) {
        var e = data[p[0]];
        return '<li><span class="rl-ref">' + e.h + ' <span class="rl-where">together in ' + p[1] + (p[1] === 1 ? " syllabus" : " syllabi") + "</span></span></li>";
      }).join("");
      panel.hidden = false;
      // keep the panel in view on small screens
      if (window.innerWidth < 760) panel.scrollIntoView({ block: "nearest" });
    }

    svg.addEventListener("click", function (e) {
      var c = e.target.closest(".nw-n");
      if (c) select(c.dataset.i); else if (e.target === svg || e.target.closest(".nw-edges")) clear();
    });
    svg.addEventListener("keydown", function (e) {
      var c = e.target.closest(".nw-n");
      if (c && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); select(c.dataset.i); }
      if (e.key === "Escape") clear();
    });
  });
})();
