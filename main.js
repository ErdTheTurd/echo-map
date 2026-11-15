/* Sonarlark site — scroll reveals, parallax, hero plan draw-in. Local only. */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function initReveals() {
    var nodes = document.querySelectorAll(".reveal");
    if (!nodes.length) return;

    if (reduceMotion || !("IntersectionObserver" in window)) {
      nodes.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );

    nodes.forEach(function (el) {
      observer.observe(el);
    });
  }

  function initParallax() {
    if (reduceMotion) return;

    var targets = Array.prototype.slice.call(
      document.querySelectorAll("[data-parallax]")
    );
    if (!targets.length) return;

    var ticking = false;

    function update() {
      var midY = window.innerHeight * 0.5;
      targets.forEach(function (el) {
        var depth = parseFloat(el.getAttribute("data-depth") || "0.06");
        var rect = el.getBoundingClientRect();
        var center = rect.top + rect.height * 0.5;
        var delta = (center - midY) * depth;
        el.style.setProperty("--px", "0px");
        el.style.setProperty("--py", delta.toFixed(2) + "px");
      });
      ticking = false;
    }

    function onScroll() {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    }

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
  }

  function initHeroPlan() {
    var host = document.querySelector("[data-hero-plan]");
    if (!host) return;

    var src = host.getAttribute("data-hero-plan");
    if (!src) return;

    function finish(staticMode) {
      host.classList.add(staticMode ? "is-static" : "is-drawn");
    }

    fetch(src)
      .then(function (res) {
        if (!res.ok) throw new Error("hero plan fetch failed");
        return res.text();
      })
      .then(function (xml) {
        host.innerHTML = xml;
        var svg = host.querySelector("svg");
        if (svg) {
          svg.setAttribute("focusable", "false");
          svg.removeAttribute("width");
          svg.removeAttribute("height");
        }
        if (reduceMotion) {
          finish(true);
          return;
        }
        // Force layout, then draw once
        void host.offsetWidth;
        requestAnimationFrame(function () {
          finish(false);
        });
      })
      .catch(function () {
        // Fallback: show as image if inline fetch fails (e.g. file://)
        var img = document.createElement("img");
        img.src = src;
        img.width = 1200;
        img.height = 800;
        img.alt = "";
        img.decoding = "async";
        img.style.cssText = "position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:62% 42%;";
        host.appendChild(img);
        finish(true);
      });
  }

  function boot() {
    initHeroPlan();
    initReveals();
    initParallax();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
