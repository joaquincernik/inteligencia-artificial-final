/* Capazeta — interacciones del sitio. Sin dependencias. */
(function () {
  "use strict";

  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");
  var meta = document.querySelector('meta[name="theme-color"]');

  function syncTheme(dark) {
    if (!toggle) return;
    toggle.setAttribute("aria-pressed", String(dark));
    toggle.setAttribute("aria-label", dark ? "Activar tema claro" : "Activar tema oscuro");
    if (meta) meta.setAttribute("content", dark ? "#0b0e12" : "#f8f9fb");
  }

  syncTheme(root.classList.contains("dark"));

  if (toggle) {
    toggle.addEventListener("click", function () {
      var dark = !root.classList.contains("dark");
      root.classList.toggle("dark", dark);
      try {
        localStorage.setItem("capazeta-theme", dark ? "dark" : "light");
      } catch (e) {
        /* modo privado: el toggle sigue funcionando en esta sesión */
      }
      syncTheme(dark);
    });
  }

  /* Cerrar el menú móvil (<details>) al elegir un destino o tocar fuera. */
  var mobileMenu = document.getElementById("mobile-menu");
  if (mobileMenu) {
    mobileMenu.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        mobileMenu.removeAttribute("open");
      });
    });

    document.addEventListener("click", function (event) {
      if (mobileMenu.open && !mobileMenu.contains(event.target)) {
        mobileMenu.removeAttribute("open");
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && mobileMenu.open) {
        mobileMenu.removeAttribute("open");
      }
    });
  }

  /* Scroll-spy del nav. */
  var navLinks = Array.prototype.slice.call(document.querySelectorAll("[data-nav]"));
  if (navLinks.length) {
    var sections = navLinks
      .map(function (link) {
        var id = link.getAttribute("href").slice(1);
        return document.getElementById(id);
      })
      .filter(Boolean);

    var ticking = false;

    function setActive() {
      ticking = false;
      var y = window.scrollY + 160;
      var activeId = null;

      sections.forEach(function (section) {
        if (section.offsetTop <= y) activeId = section.id;
      });

      navLinks.forEach(function (link) {
        var isActive = link.getAttribute("href") === "#" + activeId;
        link.classList.toggle("nav-active", isActive);
        if (isActive) {
          link.setAttribute("aria-current", "true");
        } else {
          link.removeAttribute("aria-current");
        }
      });
    }

    window.addEventListener(
      "scroll",
      function () {
        if (!ticking) {
          ticking = true;
          window.requestAnimationFrame(setActive);
        }
      },
      { passive: true },
    );

    setActive();
  }

  /* Aparición al hacer scroll (solo si hay soporte y no se pidió movimiento reducido). */
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if ("IntersectionObserver" in window && !reduceMotion) {
    root.classList.add("js");
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.06, rootMargin: "0px 0px -40px 0px" },
    );

    document.querySelectorAll("[data-reveal]").forEach(function (el) {
      observer.observe(el);
    });
  }
})();
