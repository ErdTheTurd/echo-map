/* Sonarlark site — scroll reveals + light parallax. Local only. */
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initReveals();
      initParallax();
    });
  } else {
    initReveals();
    initParallax();
  }
})();
