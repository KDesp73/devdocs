/* devdocs — front end behaviour: sidebar tree, mermaid rendering and the
 * zoomable diagram viewer. No build step, no dependencies beyond the Mermaid
 * bundle loaded from the CDN.
 */
(function () {
  "use strict";

  var config = { mermaid: { theme: "neutral" } };
  var configEl = document.getElementById("devdocs-config");
  if (configEl) {
    try {
      var parsed = JSON.parse(configEl.textContent || "{}");
      if (parsed && typeof parsed === "object") {
        if (parsed.mermaid) {
          config.mermaid = Object.assign(config.mermaid, parsed.mermaid);
        }
      }
    } catch (err) {
      /* keep defaults */
    }
  }

  /* ------------------------------------------------------------------ */
  /* sidebar                                                             */
  /* ------------------------------------------------------------------ */
  var nav = document.querySelector("nav");
  if (nav) {
    nav.addEventListener("click", function (event) {
      var toggle = event.target.closest(".nav-folder-toggle");
      if (!toggle) return;
      var folder = toggle.closest(".nav-folder");
      var items = folder ? folder.querySelector(":scope > .nav-folder-items") : null;
      if (!items) return;
      var open = folder.classList.toggle("open");
      items.classList.toggle("open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  /* ------------------------------------------------------------------ */
  /* mermaid                                                             */
  /* ------------------------------------------------------------------ */
  var nodes = document.querySelectorAll(".mermaid");
  if (!nodes.length) return;

  var MIN_SCALE = 0.4; /* never shrink an inline diagram below this */
  var MAX_SCALE = 2; /* never blow a diagram up past this in the viewer */
  var MIN_ZOOM = 0.05;
  var MAX_ZOOM = 8;
  var MAX_INLINE_HEIGHT_RATIO = 0.8;

  var dialog = document.getElementById("mermaid-dialog");
  var viewport = document.getElementById("mermaid-dialog-viewport");
  var canvas = document.getElementById("mermaid-dialog-canvas");
  var titleEl = document.getElementById("mermaid-dialog-title");
  var zoomInBtn = document.getElementById("mermaid-zoom-in");
  var zoomOutBtn = document.getElementById("mermaid-zoom-out");
  var zoomResetBtn = document.getElementById("mermaid-zoom-reset");
  var zoomFitBtn = document.getElementById("mermaid-zoom-fit");
  var zoomLevelEl = document.getElementById("mermaid-zoom-level");
  var closeBtn = document.getElementById("mermaid-dialog-close");

  var scale = 1;
  var panX = 0;
  var panY = 0;
  var dragging = false;
  var dragStartX = 0;
  var dragStartY = 0;
  var panStartX = 0;
  var panStartY = 0;

  function intrinsicSize(svg) {
    var box = svg.viewBox && svg.viewBox.baseVal;
    if (box && box.width > 0 && box.height > 0) {
      return { w: box.width, h: box.height };
    }
    try {
      var bbox = svg.getBBox();
      if (bbox.width > 0 && bbox.height > 0) return { w: bbox.width, h: bbox.height };
    } catch (err) {
      /* getBBox throws when the element is not rendered yet */
    }
    return { w: svg.clientWidth || 1, h: svg.clientHeight || 1 };
  }

  /* Mermaid injects `width="100%"` plus an inline max-width/background, which
   * is what makes large diagrams collapse to an unreadable size. Take the
   * diagram out of that flow and let it be sized explicitly. */
  function stage(svg) {
    var parent = svg.parentElement;
    if (parent && parent.classList.contains("mermaid-stage")) return parent;
    var holder = document.createElement("div");
    holder.className = "mermaid-stage";
    svg.parentNode.insertBefore(holder, svg);
    holder.appendChild(svg);
    return holder;
  }

  function prepare(node) {
    var svg = node.querySelector("svg");
    if (!svg) return null;
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    svg.style.removeProperty("max-width");
    svg.style.removeProperty("max-height");
    svg.style.removeProperty("background-color");
    stage(svg);
    var size = intrinsicSize(svg);
    node.dataset.diagramWidth = size.w;
    node.dataset.diagramHeight = size.h;
    return size;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function sizeTo(svg, size, factor) {
    svg.style.width = Math.round(size.w * factor) + "px";
    svg.style.height = Math.round(size.h * factor) + "px";
  }

  function fitInline(node) {
    var size = prepare(node);
    if (!size) return;
    var svg = node.querySelector("svg");
    var style = window.getComputedStyle(node);
    var padX = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
    var padY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
    var available = Math.max(160, node.clientWidth - padX);
    var maxHeight = Math.max(240, window.innerHeight * MAX_INLINE_HEIGHT_RATIO - padY);
    /* 1 keeps the diagram at its natural size; only shrink when it does not
     * fit, and never past the point where labels become unreadable. */
    var factor = clamp(Math.min(1, available / size.w, maxHeight / size.h), MIN_SCALE, 1);
    sizeTo(svg, size, factor);
  }

  function applyTransform() {
    if (!canvas) return;
    canvas.style.transform =
      "translate(calc(-50% + " + panX + "px), calc(-50% + " + panY + "px)) scale(" + scale + ")";
    if (zoomLevelEl) zoomLevelEl.textContent = Math.round(scale * 100) + "%";
  }

  function setScale(value) {
    scale = clamp(value, MIN_ZOOM, MAX_ZOOM);
    applyTransform();
  }

  function resetView() {
    panX = 0;
    panY = 0;
    setScale(1);
  }

  function naturalSize() {
    if (!canvas) return null;
    var node = canvas.querySelector(".mermaid");
    if (!node) return null;
    var w = parseFloat(node.dataset.diagramWidth || "0");
    var h = parseFloat(node.dataset.diagramHeight || "0");
    if (w > 0 && h > 0) return { w: w, h: h };
    var svg = canvas.querySelector("svg");
    return svg ? intrinsicSize(svg) : null;
  }

  function fitToView() {
    var size = naturalSize();
    if (!size || !viewport) return;
    var pad = 56;
    var availableW = Math.max(80, viewport.clientWidth - pad);
    var availableH = Math.max(80, viewport.clientHeight - pad);
    panX = 0;
    panY = 0;
    setScale(clamp(Math.min(availableW / size.w, availableH / size.h), MIN_ZOOM, MAX_SCALE));
  }

  function zoomBy(factor) {
    setScale(scale * factor);
  }

  function closeDialog() {
    if (dialog && dialog.open) dialog.close();
    if (canvas) canvas.textContent = "";
    resetView();
  }

  function fallback(node, source) {
    node.classList.remove("mermaid");
    var pre = document.createElement("pre");
    pre.className = "codehilite";
    pre.textContent = source;
    var hint = node.nextElementSibling;
    if (hint && hint.classList.contains("mermaid-hint")) hint.remove();
    node.replaceWith(pre);
  }

  function wirePreview(node) {
    var source = node.textContent.trim();
    if (!source) return;
    node.dataset.mermaidSource = source;
    node.setAttribute("role", "button");
    node.setAttribute("tabindex", "0");
    node.setAttribute("aria-label", "Open diagram to explore");
    node.addEventListener("click", function () {
      openDialog(source);
    });
    node.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openDialog(source);
      }
    });
    var hint = document.createElement("span");
    hint.className = "mermaid-hint";
    hint.textContent = "Click to explore";
    node.insertAdjacentElement("afterend", hint);
  }

  function openDialog(source) {
    if (!dialog || !canvas || typeof mermaid === "undefined") return;
    var node = document.createElement("div");
    node.className = "mermaid";
    node.id = "mermaid-modal-diagram";
    node.textContent = source;
    canvas.textContent = "";
    canvas.appendChild(node);
    if (titleEl) titleEl.textContent = "Diagram";
    resetView();
    dialog.showModal();
    mermaid
      .run({ nodes: [node] })
      .then(function () {
        var size = prepare(node);
        /* The viewer scales the canvas with a transform, so the diagram
         * itself has to stay at its natural size. */
        if (size) sizeTo(node.querySelector("svg"), size, 1);
        fitToView();
      })
      .catch(function (err) {
        console.error("Mermaid render failed:", err);
      });
  }

  function renderAll() {
    if (typeof mermaid === "undefined") {
      Array.prototype.forEach.call(nodes, function (node) {
        fallback(node, node.dataset.mermaidSource || node.textContent.trim());
      });
      return;
    }
    mermaid
      .run({ nodes: Array.prototype.slice.call(nodes) })
      .then(function () {
        Array.prototype.forEach.call(nodes, fitInline);
      })
      .catch(function (err) {
        console.error("Mermaid render failed:", err);
      });
  }

  /* ---- wiring ---- */
  if (typeof mermaid !== "undefined") {
    mermaid.initialize({
      startOnLoad: false,
      theme: config.mermaid.theme || "neutral",
      securityLevel: "strict",
      useMaxWidth: false,
      fontFamily: getComputedStyle(document.body).fontFamily,
    });
  }

  Array.prototype.forEach.call(nodes, wirePreview);
  renderAll();

  var resizeTimer = null;
  window.addEventListener("resize", function () {
    if (resizeTimer) window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      Array.prototype.forEach.call(nodes, fitInline);
    }, 150);
  });

  if (!dialog || !viewport || !canvas) return;

  viewport.addEventListener(
    "wheel",
    function (event) {
      if (!dialog.open) return;
      event.preventDefault();
      zoomBy(event.deltaY > 0 ? 0.9 : 1.1);
    },
    { passive: false }
  );

  viewport.addEventListener("dblclick", function () {
    if (dialog.open) fitToView();
  });

  viewport.addEventListener("mousedown", function (event) {
    if (!dialog.open || event.button !== 0) return;
    dragging = true;
    dragStartX = event.clientX;
    dragStartY = event.clientY;
    panStartX = panX;
    panStartY = panY;
    viewport.classList.add("is-dragging");
  });

  window.addEventListener("mousemove", function (event) {
    if (!dragging) return;
    panX = panStartX + (event.clientX - dragStartX);
    panY = panStartY + (event.clientY - dragStartY);
    applyTransform();
  });

  window.addEventListener("mouseup", function () {
    dragging = false;
    viewport.classList.remove("is-dragging");
  });

  zoomInBtn.addEventListener("click", function () {
    zoomBy(1.2);
  });
  zoomOutBtn.addEventListener("click", function () {
    zoomBy(1 / 1.2);
  });
  zoomResetBtn.addEventListener("click", resetView);
  zoomFitBtn.addEventListener("click", fitToView);
  closeBtn.addEventListener("click", closeDialog);
  dialog.addEventListener("close", closeDialog);
  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) closeDialog();
  });
  dialog.addEventListener("cancel", function (event) {
    event.preventDefault();
    closeDialog();
  });
  /* Some browsers do not fire ``cancel`` for a synthetic Escape, and the
   * dialog is a modal top layer, so listen for the key as well. */
  dialog.addEventListener("keydown", function (event) {
    if (event.key === "Escape" || event.key === "Esc") closeDialog();
  });
  document.addEventListener("keydown", function (event) {
    if (dialog.open && (event.key === "Escape" || event.key === "Esc")) closeDialog();
  });
})();
