// =============================================================================
// FILE: static/js/app.js — all the browser-side behaviour of the website.
// Search for the section name below to jump to it:
//   header ............... header shadow on scroll, mobile menu
//   toasts ............... small pop-up messages
//   press feedback ....... button loading spinner when a form is submitted
//   top line ............. coloured loading line when you click a link
//   pointer trail ........ thin red line that follows the mouse
//   reveal on scroll ..... fade-in, word-by-word headings, number count-up, progress bars
//   scroll motion ........ pinned "how it works" cards, parallax, footer light-up, the parrot (tota)
//   before / after ....... drag slider to compare before and after photos
//   password tools ....... show/hide password, strength meter, "passwords match" check
//   live validation ...... checks form fields while typing (same rules as the server)
//   photo dropzone ....... checks photo type and size before upload
//   multi-step wizard .... the 4-step "Report a problem" and 2-step sign-up forms
//   geolocation .......... "Use my location" button (GPS)
//   upvote ............... upvote without reloading the page
//   admin ................ admin sidebar (collapse, mobile drawer) and Ctrl+K command palette
//   charts ............... Chart.js colours; charts draw when they scroll into view
//   PWA .................. lets the website be installed like an app
// NOTE: the real validation always happens again on the server (forms.py); this is only for quick feedback.
// =============================================================================
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const haptic = (ms = 8) => { try { navigator.vibrate && navigator.vibrate(ms); } catch (e) {} };

  // ---------------------------------------------------------------- header
  const header = $(".site-header");
  if (header) {
    let ticking = false;
    const update = () => { header.classList.toggle("scrolled", scrollY > 4); ticking = false; };
    addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    update();
    const t = $(".nav-toggle");
    t && t.addEventListener("click", () => header.classList.toggle("menu-open"));
  }
  $$(".account").forEach((acc) => {
    const btn = $(".account-btn", acc), menu = $(".menu", acc);
    btn && btn.addEventListener("click", (e) => { e.stopPropagation(); menu.classList.toggle("open"); });
    document.addEventListener("click", (e) => { if (!acc.contains(e.target)) menu.classList.remove("open"); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") menu.classList.remove("open"); });
  });

  // ---------------------------------------------------------------- toasts
  const closeToast = (t) => { t.classList.add("hide"); setTimeout(() => t.remove(), 220); };
  $$(".toast").forEach((t, i) => {
    const b = $("button", t); b && b.addEventListener("click", () => closeToast(t));
    setTimeout(() => closeToast(t), 5000 + i * 500);
  });
  window.SSToast = (msg, kind = "success") => {
    let wrap = $(".toasts");
    if (!wrap) { wrap = document.createElement("div"); wrap.className = "toasts"; document.body.appendChild(wrap); }
    const t = document.createElement("div");
    t.className = `toast ${kind}`;
    t.innerHTML = `<span class="t-ico">${kind === "error" ? "!" : "✓"}</span><span style="padding-top:2px"></span>`;
    t.children[1].textContent = msg;
    wrap.appendChild(t);
    setTimeout(() => closeToast(t), 3500);
  };

  // ---------------------------------------------------------------- press feedback + loading state
  document.addEventListener("pointerdown", (e) => { if (e.target.closest(".btn, .vote, .tabbar a")) haptic(6); });
  $$("form").forEach((f) => f.addEventListener("submit", () => {
    if (f.dataset.noLoading !== undefined) return;
    const b = f.querySelector("button[type=submit]");
    if (b) setTimeout(() => b.classList.add("loading"), 0);
  }));
  addEventListener("pageshow", () => $$(".btn.loading").forEach((b) => b.classList.remove("loading")));

  // ---------------------------------------------------------------- top line while the next page loads
  const navLine = document.createElement("div");
  navLine.className = "nav-line"; document.body.appendChild(navLine);
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[href]");
    if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.target === "_blank" || a.hasAttribute("download") || a.hasAttribute("data-no-transition")) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || (url.pathname === location.pathname && url.search === location.search)) return;
    navLine.classList.add("go");
  });
  document.addEventListener("submit", (e) => { if (!e.target.hasAttribute("data-no-loading")) navLine.classList.add("go"); });
  addEventListener("pageshow", () => navLine.classList.remove("go"));

  // ---------------------------------------------------------------- pointer trail: a thin line that follows the cursor
  if (finePointer && !reduced) {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "trail");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS(NS, "path");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#DC3B3B");
    path.setAttribute("stroke-width", "1.6");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    svg.appendChild(path);
    document.body.appendChild(svg);
    const pts = [];
    let running = false, last = 0;
    const draw = (now) => {
      while (pts.length && now - pts[0].t > 260) pts.shift();
      if (pts.length > 1) {
        let d = `M${pts[0].x},${pts[0].y}`;
        for (let i = 1; i < pts.length - 1; i++) {
          const mx = (pts[i].x + pts[i + 1].x) / 2, my = (pts[i].y + pts[i + 1].y) / 2;
          d += ` Q${pts[i].x},${pts[i].y} ${mx},${my}`;
        }
        const end = pts[pts.length - 1];
        d += ` L${end.x},${end.y}`;
        path.setAttribute("d", d);
        path.setAttribute("opacity", Math.min(1, pts.length / 12) * 0.55);
      } else path.setAttribute("d", "");
      if (pts.length) requestAnimationFrame(draw); else running = false;
    };
    addEventListener("pointermove", (e) => {
      if (e.pointerType !== "mouse") return;
      const now = performance.now();
      if (now - last < 12) return;
      last = now;
      pts.push({ x: e.clientX, y: e.clientY, t: now });
      if (pts.length > 24) pts.shift();
      if (!running) { running = true; requestAnimationFrame(draw); }
    }, { passive: true });
  }

  // ---------------------------------------------------------------- reveal on scroll, counters, bars
  const countUp = (el) => {
    const target = parseFloat(el.dataset.count || "0"), dec = (el.dataset.count || "").includes(".") ? 1 : 0;
    const fmt = (v) => v.toLocaleString("en-IN", { minimumFractionDigits: dec, maximumFractionDigits: dec });
    if (!target || reduced) { el.textContent = fmt(target); return; }
    const start = performance.now(), dur = 900;
    const tick = (now) => {
      const p = Math.min(1, (now - start) / dur);
      el.textContent = fmt(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const activate = (el) => {
    el.classList.add("in");
    if (el.hasAttribute("data-words")) el.classList.add("words-in");
    const own = el.matches("[data-count]") ? [el] : [];
    own.concat($$("[data-count]", el)).forEach((c) => { if (!c.dataset.done) { c.dataset.done = 1; countUp(c); } });
    $$(".bar-line > i", el).forEach((b) => b.style.width = b.dataset.w + "%");
    $$(".tracker .fill", el).forEach((f) => f.style.width = f.dataset.w + "%");
  };
  const autoStagger = (sel, step) => $$(sel).forEach((w) => { if (!w.hasAttribute("data-stagger")) w.setAttribute("data-stagger", step); });
  autoStagger(".c-grid", ".07"); autoStagger(".kpis", ".06"); autoStagger(".rank", ".05"); autoStagger(".track-tips", ".1");
  autoStagger(".table tbody", ".04"); autoStagger(".cleaned-grid", ".08");
  $$(".timeline").forEach((t) => $$("li", t).forEach((li, i) => li.style.setProperty("--i", Math.min(i, 8))));
  $$(".welcome .orb .ring").forEach((r) => r.style.setProperty("--len", (r.getAttribute("stroke-dasharray") || "503").split(" ")[0]));
  $$("[data-stagger]").forEach((wrap) => {
    const step = parseFloat(wrap.dataset.stagger) || 0.06;
    Array.from(wrap.children).forEach((c, i) => {
      if (!c.hasAttribute("data-reveal")) c.setAttribute("data-reveal", "");
      c.style.setProperty("--d", `${Math.min(i, 6) * step}s`);
    });
  });
  // Split headings into words so they can rise one after another.
  const splitWords = (el) => {
    let i = 0;
    const walk = (node) => {
      Array.from(node.childNodes).forEach((ch) => {
        if (ch.nodeType === 3) {
          const frag = document.createDocumentFragment();
          ch.textContent.split(/(\s+)/).forEach((part) => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(" ")); return; }
            const w = document.createElement("span"), wi = document.createElement("span");
            w.className = "w"; wi.className = "wi"; wi.style.setProperty("--i", i++); wi.textContent = part;
            w.appendChild(wi); frag.appendChild(w);
          });
          ch.replaceWith(frag);
        } else if (ch.nodeType === 1 && ch.tagName !== "BR") walk(ch);
      });
    };
    walk(el);
  };
  if (!reduced) $$("[data-words]").forEach(splitWords);

  const targets = $$("[data-reveal], [data-count], [data-clip], [data-words], .bar-line, .tracker, .timeline, .page-head, .podium, .welcome");
  if ("IntersectionObserver" in window && !reduced) {
    const io = new IntersectionObserver((entries) => entries.forEach((en) => {
      if (en.isIntersecting) { activate(en.target); io.unobserve(en.target); }
    }), { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });
    targets.forEach((t) => io.observe(t));
    // Safety net: whatever is already on screen must never stay hidden, even if the observer is slow.
    const sweep = () => targets.forEach((t) => {
      if (t.classList.contains("in")) return;
      const r = t.getBoundingClientRect();
      if (r.top < innerHeight && r.bottom > 0) { activate(t); io.unobserve(t); }
    });
    requestAnimationFrame(sweep); setTimeout(sweep, 600); addEventListener("load", sweep);
  } else targets.forEach(activate);


  // ---------------------------------------------------------------- scroll motion (GSAP ScrollTrigger, native scroll)
  if (window.gsap && window.ScrollTrigger && !reduced) {
    gsap.registerPlugin(ScrollTrigger);

    // "How it works": the section pins and the cards slide in from the side one by one.
    const how = $(".how");
    if (how && innerWidth > 880) {
      const track = $(".how-track", how), bar = $(".how-progress i", how);
      const dist = () => Math.max(0, track.scrollWidth - innerWidth);
      const slide = gsap.to(track, {
        x: () => -dist(), ease: "none",
        scrollTrigger: {
          trigger: how, start: "top top", end: () => "+=" + dist(), pin: true, scrub: 0.6,
          anticipatePin: 1, invalidateOnRefresh: true,
          onUpdate: (st) => { if (bar) bar.style.transform = `scaleX(${st.progress})`; },
        },
      });
      $$(".how-card", how).forEach((card, i) => {
        if (i === 0) return;
        gsap.from(card, {
          y: 80, rotate: 3, opacity: 0.2, ease: "power2.out",
          scrollTrigger: { trigger: card, containerAnimation: slide, start: "left 98%", end: "left 60%", scrub: true },
        });
      });
    } else if (how) {
      // Phones: cards stack, and each one rises and settles as it scrolls in.
      $$(".how-card", how).forEach((card) => {
        gsap.from(card, { y: 60, scale: 0.94, opacity: 0, ease: "power2.out", scrollTrigger: { trigger: card, start: "top 95%", end: "top 70%", scrub: 0.5 } });
      });
    }

    // Gentle parallax for mockups.
    $$("[data-speed]").forEach((el) => {
      gsap.to(el, {
        yPercent: parseFloat(el.dataset.speed) * 100, ease: "none",
        scrollTrigger: { trigger: el.closest("section") || el, start: "top bottom", end: "bottom top", scrub: true },
      });
    });

    // Big blocks grow into place as they enter.
    $$("[data-grow]").forEach((el) => {
      gsap.fromTo(el, { scale: 0.93 }, { scale: 1, ease: "none", scrollTrigger: { trigger: el, start: "top bottom", end: "top 50%", scrub: true } });
    });

    // The crossing bands drift a little with the scroll, on top of their own loop.
    $$(".bands .band").forEach((band, i) => {
      gsap.fromTo(band, { xPercent: i ? -3 : 3 }, { xPercent: i ? 3 : -3, ease: "none", scrollTrigger: { trigger: ".bands", start: "top bottom", end: "bottom top", scrub: true } });
    });


    // Footer wordmark: letters light up one by one as you scroll to the bottom, and dim again on the way up.
    $$("[data-light]").forEach((el) => {
      const text = el.textContent; el.textContent = "";
      const letters = [];
      Array.from(text).forEach((ch) => {
        const sp = document.createElement("span");
        if (ch === " ") { sp.className = "sp"; el.appendChild(sp); return; }
        sp.className = "lt"; sp.textContent = ch; el.appendChild(sp); letters.push(sp);
      });
      const split = text.indexOf(" ");
      const tl = gsap.timeline({ scrollTrigger: { trigger: el.closest("footer") || el, start: "top 85%", end: "bottom bottom", scrub: 0.8 } });
      tl.fromTo(letters, { yPercent: 35, rotate: (i) => (i % 2 ? 6 : -6), color: "#22322A", textShadow: "0 0 0 rgba(242,179,61,0)" }, {
        yPercent: 0, rotate: 0, ease: "power2.out", stagger: 0.08,
        color: (i) => (i >= split ? "#F2B33D" : "#F4EEE1"),
        textShadow: (i) => (i >= split ? "0 0 38px rgba(242,179,61,.45)" : "0 0 30px rgba(244,238,225,.18)"),
      });
    });

    // The tota (rose-ringed parakeet). It reacts to scroll the moment it happens: a quick scroll startles it and it flies,
    // holding its spot on screen while the page moves under it; when you stop, it lands on a nearby heading or card.
    // While sitting it tilts its head, blinks and sways its tail, turns to look at your cursor, and moves if you click it.
    if (document.querySelector(".site-footer")) {
      const bird = document.createElement("div");
      bird.className = "birdie left"; bird.setAttribute("aria-hidden", "true");
      bird.innerHTML = `<div class="b-flip"><div class="b-in"><svg viewBox="0 0 60 90" fill="none">
        <defs>
          <linearGradient id="pt-tail" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A9E38"/><stop offset=".5" stop-color="#2B9677"/><stop offset="1" stop-color="#3A78B5"/></linearGradient>
          <radialGradient id="pt-body" cx=".7" cy=".32" r=".85"><stop offset="0" stop-color="#A4EA74"/><stop offset=".5" stop-color="#5FBE40"/><stop offset="1" stop-color="#2C862B"/></radialGradient>
          <linearGradient id="pt-wing" x1="0" y1="0" x2=".2" y2="1"><stop offset="0" stop-color="#3F9E35"/><stop offset=".65" stop-color="#2A7429"/><stop offset="1" stop-color="#1D5527"/></linearGradient>
          <radialGradient id="pt-head" cx=".65" cy=".35" r=".75"><stop offset="0" stop-color="#ACEF7E"/><stop offset=".7" stop-color="#63C444"/><stop offset="1" stop-color="#3C9734"/></radialGradient>
          <linearGradient id="pt-beak" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F4474D"/><stop offset="1" stop-color="#B0141B"/></linearGradient>
        </defs>
        <ellipse class="shadow" cx="30" cy="61.4" rx="9" ry="1.5" fill="rgba(21,33,27,.22)"/>
        <g class="pose">
          <g class="tail">
            <path d="M25.5 55 L23.2 88 Q25.6 89.6 27.8 88 L30 56 Z" fill="url(#pt-tail)"/>
            <path d="M28.6 56 L31 85.5 Q32.6 86.2 33.8 84.8 L32 56 Z" fill="#2E8F7E"/>
            <path d="M26.8 58 L25.4 85" stroke="#B9E59A" stroke-width=".7" opacity=".55" stroke-linecap="round"/>
          </g>
          <g class="feet" stroke="#8B7E77" stroke-width="2.1" stroke-linecap="round">
            <path d="M27 56.5 L26.6 60.2 M33 56.5 L33.4 60.2"/>
            <path d="M22.8 60.6 h4.4 M27.6 60.6 h2.6 M30.6 60.6 h4 M34.4 60.6 h3.8" stroke-width="1.9"/>
          </g>
          <g class="wing2">
            <path d="M22 26.5 Q30.5 28 31.5 42 Q30.5 55 24.5 65 Q17.5 52 18.6 38 Q19 30.5 22 26.5 Z" fill="#1E5A26"/>
            <path d="M21 35 Q26 35.5 29.5 39 M20.6 41.5 Q25.5 42.5 28.8 46.5" stroke="#123A18" stroke-width="1" fill="none" opacity=".7" stroke-linecap="round"/>
            <path d="M23 56 Q25 61 24.5 65" stroke="#244F7A" stroke-width="2.2" stroke-linecap="round"/>
          </g>
          <g class="torso">
            <path d="M28 19.5 Q44.5 20.5 43.5 38 Q42.5 52 33.5 58 L26 58 Q17.5 49 18.8 36 Q20 22.5 28 19.5 Z" fill="url(#pt-body)"/>
            <path d="M36.5 25 Q43.5 33 41 47 Q38.5 54 33.5 56.5 Q38.8 44 36.5 25 Z" fill="#C4F29A" opacity=".55"/>
          </g>
          <g class="wing">
            <path d="M22 26.5 Q30.5 28 31.5 42 Q30.5 55 24.5 65 Q17.5 52 18.6 38 Q19 30.5 22 26.5 Z" fill="url(#pt-wing)"/>
            <path d="M21 35 Q26 35.5 29.5 39 M20.6 41.5 Q25.5 42.5 28.8 46.5 M21.2 48 Q25 49.5 27 53.5" stroke="#174A22" stroke-width="1" fill="none" opacity=".7" stroke-linecap="round"/>
            <path d="M23 56 Q25 61 24.5 65" stroke="#2C5F93" stroke-width="2.2" stroke-linecap="round"/>
          </g>
          <g class="head">
            <circle cx="32" cy="13.6" r="9.6" fill="url(#pt-head)"/>
            <path d="M23.6 17.6 Q31 25.2 40.2 18.6" stroke="#141414" stroke-width="2.2" fill="none" stroke-linecap="round"/>
            <path d="M24.8 20.1 Q31.6 27.2 39.6 21" stroke="#F08BB0" stroke-width="1.6" fill="none" stroke-linecap="round"/>
            <path d="M37.2 16.6 Q40 18.2 40.6 20.2" stroke="#141414" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <g class="eye"><circle cx="35.4" cy="11.4" r="2.35" fill="#F5E27A"/><circle cx="35.8" cy="11.4" r="1.35" fill="#111"/><circle cx="36.3" cy="10.8" r=".45" fill="#fff"/></g>
            <path d="M32.6 8.8 Q35.6 7.1 38.6 8.9" stroke="#24611F" stroke-width="1.3" fill="none" stroke-linecap="round"/>
            <path d="M38.6 9.2 Q47.8 8.2 46.8 17.4 Q45.2 13.8 40.6 14.6 Z" fill="url(#pt-beak)"/>
            <path d="M40.4 14.4 Q44.1 14.6 44.3 17.7 Q41.6 18.1 40.1 15.9 Z" fill="#7E1418"/>
            <path d="M40.2 10.3 Q43.8 10 45.4 12.3" stroke="#FF8A8E" stroke-width=".8" fill="none" opacity=".7" stroke-linecap="round"/>
          </g>
        </g>
      </svg></div></div>`;
      document.body.appendChild(bird);
      const inner = $(".b-in", bird);
      const FOOT_X = 30 / 60, FOOT_Y = 60.6 / 90;
      const pos = { x: innerWidth + 70, y: scrollY + innerHeight * 0.25 }, vel = { x: -8, y: 0 };
      let mode = "follow", perch = null, raf = 0, last = 0, facingLeft = true, idleT = 0, sitT = 0, fidgetT = 0;
      let lastSY = scrollY, startle = 0;

      const draw = (tilt = 0) => {
        const w = bird.offsetWidth, h = bird.offsetHeight;
        gsap.set(bird, { x: pos.x - w * FOOT_X, y: pos.y - h * FOOT_Y, rotate: tilt });
      };
      // Nose up when climbing (up to 16deg), only a slight dip when coming down (max 6deg): proud, never droopy.
      const tiltOf = () => Math.max(-16, Math.min(6, vel.y * 1.3)) * (facingLeft ? -1 : 1);
      const face = (left) => { if (left !== facingLeft) { facingLeft = left; bird.classList.toggle("left", left); } };
      const band = () => [scrollY + 96, scrollY + innerHeight - (document.querySelector(".tabbar") ? 150 : 90)];

      const SEL = "main h1, main h2, .footer-big, main .card, main .c-card, main .kpi, main .cat-card, main .photo-frame, main .welcome, main .rank-row, main .pod, main .tip, main .cleaned";
      const isText = (el) => /^H[12]$/.test(el.tagName) || el.classList.contains("footer-big");
      const pointOf = (el) => {
        if (!el.isConnected || !el.offsetParent) return null;
        const vw = document.documentElement.clientWidth;
        if (isText(el)) {
          const r = document.createRange(); r.selectNodeContents(el);
          const rects = Array.from(r.getClientRects()).filter((q) => q.width > 4 && q.height > 4);
          if (!rects.length) return null;
          const first = rects.reduce((a, b) => (b.top < a.top ? b : a));
          let right = first.left;
          rects.forEach((q) => { if (Math.abs(q.top - first.top) < first.height * 0.5) right = Math.max(right, q.right); });
          return { el, text: true, x: Math.min(Math.max(right - 16, 30), vw - 34) + scrollX, y: first.top + scrollY + first.height * 0.24 };
        }
        const b = el.getBoundingClientRect();
        if (b.width < 120) return null;
        return { el, text: false, x: Math.min(b.left + b.width * 0.78, b.right - 34, vw - 34) + scrollX, y: b.top + scrollY + 1 };
      };
      const findPerch = (avoid) => {
        const [lo, hi] = band(); let best = null, bestD = Infinity;
        $$(SEL).forEach((el) => {
          if (el === avoid || el.closest(".how, .bands, [data-speed], .palette, .menu")) return;
          const pt = pointOf(el); if (!pt || pt.y < lo || pt.y > hi) return;
          const d = Math.hypot(pt.x - pos.x, (pt.y - pos.y) * 1.4) - (pt.text ? 260 : 0);
          if (d < bestD) { bestD = d; best = pt; }
        });
        return best;
      };

      const step = (now) => {
        const dt = last ? Math.min(3, (now - last) / 16.67) : 1; last = now;
        let tx, ty, k;
        if (mode === "land" && perch) {
          const p = pointOf(perch.el) || perch; perch = p;
          const dx = p.x - pos.x;
          tx = p.x; ty = Math.abs(dx) > 26 ? p.y - Math.min(80, Math.abs(dx) * 0.4) : p.y; k = 0.075;
          if (Math.hypot(p.x - pos.x, p.y - pos.y) < 2.5 && Math.hypot(vel.x, vel.y) < 1.6) return land();
        } else {
          const vw = document.documentElement.clientWidth;
          tx = Math.min(Math.max(pos.x, 80), vw - 80) + Math.sin(now / 900) * 40;
          ty = scrollY + innerHeight * 0.3 + Math.sin(now / 330) * 9; k = 0.06;
        }
        const damp = Math.pow(0.8, dt);
        vel.x = (vel.x + (tx - pos.x) * k * dt) * damp;
        vel.y = (vel.y + (ty - pos.y) * k * dt) * damp;
        const sp = Math.hypot(vel.x, vel.y), max = 30;
        if (sp > max) { vel.x *= max / sp; vel.y *= max / sp; }
        pos.x += vel.x * dt; pos.y += vel.y * dt;
        if (Math.abs(vel.x) > 0.8) face(vel.x < 0);
        bird.classList.toggle("glide", vel.y > 1.2 && sp < 14);
        draw(tiltOf());
        raf = requestAnimationFrame(step);
      };
      const fly = () => {
        clearInterval(sitT); clearTimeout(fidgetT);
        bird.classList.add("fly"); bird.classList.remove("look", "stretch", "bob");
        if (!raf) { last = 0; raf = requestAnimationFrame(step); }
      };
      const takeOff = (to) => {
        if (mode === "perched") { vel.y = -8; vel.x = (facingLeft ? -1 : 1) * 4; }
        perch = to || null; mode = to ? "land" : "follow"; fly();
      };
      // Small one-off moves (wing stretch, head bob) are CSS classes that remove themselves.
      let playT = 0;
      const play = (cls, ms) => {
        bird.classList.remove("stretch", "bob"); void bird.offsetWidth;
        bird.classList.add(cls); clearTimeout(playT);
        playT = setTimeout(() => bird.classList.remove(cls), ms);
      };
      const fidget = () => {
        fidgetT = setTimeout(() => {
          if (mode !== "perched") return;
          const r = Math.random();
          if (r < 0.3) {             // sharp look over the shoulder and back
            face(!facingLeft); setTimeout(() => mode === "perched" && face(!facingLeft), 700 + Math.random() * 900);
          } else if (r < 0.55) {     // wing stretch, like shaking out the feathers
            play("stretch", 800);    // CSS keyframes only: GSAP never touches the SVG parts (it broke their pivot points)
          } else if (r < 0.75) {     // hop and turn
            gsap.timeline().to(inner, { y: -10, duration: 0.13, ease: "power2.out", onComplete: () => face(!facingLeft) }).to(inner, { y: 0, duration: 0.22, ease: "bounce.out" });
          } else {                   // quick head bob, alert
            play("bob", 450);
          }
          fidget();
        }, 2200 + Math.random() * 3200);
      };
      const land = () => {
        cancelAnimationFrame(raf); raf = 0;
        pos.x = perch.x; pos.y = perch.y; vel.x = vel.y = 0; mode = "perched"; startle = 0;
        draw(0); bird.classList.remove("fly", "glide");
        gsap.fromTo(inner, { scaleY: 0.86, scaleX: 1.06, transformOrigin: "50% 67%" }, { scaleY: 1, scaleX: 1, duration: 0.5, ease: "elastic.out(1, .45)" });
        face(pos.x - scrollX > document.documentElement.clientWidth / 2);
        sitT = setInterval(() => {
          const p = perch && pointOf(perch.el);
          if (!p) return takeOff();
          if (Math.abs(p.x - pos.x) > 1.5 || Math.abs(p.y - pos.y) > 1.5) { pos.x = p.x; pos.y = p.y; draw(0); }
        }, 400);
        fidget();
      };
      const settle = () => {
        if (mode === "perched") return;
        const p = findPerch();
        if (p) { perch = p; mode = "land"; fly(); } else { idleT = setTimeout(settle, 700); }
      };

      // Scroll: react on the very same event, no waiting.
      addEventListener("scroll", () => {
        const dy = scrollY - lastSY; lastSY = scrollY;
        clearTimeout(idleT);
        if (mode === "perched") {
          startle += Math.abs(dy);
          const [lo, hi] = band(), p = pointOf(perch.el);
          if (Math.abs(dy) > 25 || startle > 90 || !p || p.y < lo - 20 || p.y > hi + 20) {
            pos.y += dy; draw(0);             // keep its place on screen from this very frame
            takeOff();
          }
        } else {
          pos.y += dy; draw(tiltOf());   // flies with the screen, page moves under it
          if (mode === "land") { mode = "follow"; perch = null; }
        }
        idleT = setTimeout(settle, 180);
      }, { passive: true });
      addEventListener("resize", () => { if (mode === "perched") takeOff(); clearTimeout(idleT); idleT = setTimeout(settle, 300); });

      let lookT = 0;
      document.addEventListener("pointermove", (e) => {
        if (mode !== "perched" || lookT) return;
        lookT = setTimeout(() => { lookT = 0; }, 120);
        const mx = e.clientX + scrollX, my = e.clientY + scrollY;
        const near = Math.hypot(mx - pos.x, my - (pos.y - 30)) < 170;
        bird.classList.toggle("look", near);
        if (near) face(mx < pos.x);
      }, { passive: true });
      bird.addEventListener("click", () => {
        haptic(10);
        const to = findPerch(perch && perch.el);
        if (to) takeOff(to);
        else gsap.timeline().to(inner, { y: -14, duration: 0.16, ease: "power2.out" }).to(inner, { y: 0, duration: 0.3, ease: "bounce.out" });
      });

      draw(0);
      setTimeout(() => { gsap.to(bird, { opacity: 1, duration: 0.4 }); fly(); idleT = setTimeout(settle, 500); }, 900);
    }

    addEventListener("load", () => ScrollTrigger.refresh());
  }

  // ---------------------------------------------------------------- before / after compare
  $$("[data-compare]").forEach((box) => {
    const set = (x) => {
      const r = box.getBoundingClientRect();
      box.style.setProperty("--pos", `${Math.max(2, Math.min(98, ((x - r.left) / r.width) * 100))}%`);
    };
    let drag = false;
    box.addEventListener("pointerdown", (e) => { drag = true; set(e.clientX); box.setPointerCapture(e.pointerId); });
    box.addEventListener("pointermove", (e) => { if (drag) set(e.clientX); });
    box.addEventListener("pointerup", () => { drag = false; });
    box.addEventListener("keydown", (e) => {
      const cur = parseFloat(getComputedStyle(box).getPropertyValue("--pos")) || 50;
      if (e.key === "ArrowLeft") box.style.setProperty("--pos", `${Math.max(2, cur - 5)}%`);
      if (e.key === "ArrowRight") box.style.setProperty("--pos", `${Math.min(98, cur + 5)}%`);
    });
  });

  // ---------------------------------------------------------------- forms: password tools
  const eye = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeOff = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9.9 4.2A10 10 0 0 1 12 4c7 0 10 8 10 8a13 13 0 0 1-1.7 2.7"/><path d="M6.6 6.6A13.5 13.5 0 0 0 2 12s3 8 10 8a9.7 9.7 0 0 0 5.4-1.6"/><path d="m2 2 20 20"/></svg>';
  $$("input[type=password]").forEach((inp) => {
    const wrap = document.createElement("div"); wrap.className = "pw-wrap";
    inp.parentNode.insertBefore(wrap, inp); wrap.appendChild(inp);
    const b = document.createElement("button"); b.type = "button"; b.className = "pw-toggle"; b.setAttribute("aria-label", "Show password"); b.innerHTML = eye;
    wrap.appendChild(b);
    b.addEventListener("click", () => {
      const show = inp.type === "password"; inp.type = show ? "text" : "password";
      b.innerHTML = show ? eyeOff : eye; b.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });
  $$("[data-strength]").forEach((inp) => {
    const host = inp.closest(".field") || inp.parentNode;
    const meter = document.createElement("div"); meter.className = "strength"; meter.innerHTML = "<i></i><i></i><i></i><i></i>";
    const rules = document.createElement("ul"); rules.className = "rules";
    const R = [["len", "8+ characters", (v) => v.length >= 8], ["up", "Uppercase letter", (v) => /[A-Z]/.test(v)], ["low", "Lowercase letter", (v) => /[a-z]/.test(v)],
      ["num", "Number", (v) => /\d/.test(v)], ["sym", "Special character", (v) => /[^A-Za-z0-9]/.test(v)], ["sp", "No spaces", (v) => v.length > 0 && !/\s/.test(v)]];
    rules.innerHTML = R.map(([k, t]) => `<li data-r="${k}">${t}</li>`).join("");
    host.append(meter, rules);
    const upd = () => {
      const v = inp.value; let ok = 0;
      R.forEach(([k, , fn]) => { const pass = fn(v); rules.querySelector(`[data-r=${k}]`).classList.toggle("ok", pass); ok += pass; });
      meter.dataset.s = !v ? 0 : ok <= 2 ? 1 : ok <= 4 ? 2 : ok === 5 ? 3 : 4;
      inp.setCustomValidity(ok === R.length || !v ? "" : "Password is not strong enough yet.");
    };
    inp.addEventListener("input", upd); upd();
  });
  function showLive(inp, msg) {
    const field = inp.closest(".field"); if (!field) return;
    let el = $(".live-err", field);
    if (!el) { el = document.createElement("div"); el.className = "live-err"; field.appendChild(el); }
    el.textContent = msg;
  }
  $$("[data-match]").forEach((inp) => {
    const other = document.getElementById(inp.dataset.match);
    const upd = () => {
      const bad = inp.value && other && inp.value !== other.value;
      inp.setCustomValidity(bad ? "Passwords don't match." : "");
      showLive(inp, bad ? "Passwords don't match." : "");
    };
    inp.addEventListener("input", upd); other && other.addEventListener("input", upd);
  });

  // ---------------------------------------------------------------- forms: live validation
  const friendly = (inp) => {
    const v = inp.validity, label = (inp.closest(".field")?.querySelector("label")?.textContent || "This field").replace("*", "").trim();
    if (v.valueMissing) return `${label} is required.`;
    if (v.typeMismatch) return inp.type === "email" ? "Enter a valid email address." : `Enter a valid ${label.toLowerCase()}.`;
    if (v.tooShort) return `Use at least ${inp.minLength} characters (${inp.value.length} so far).`;
    if (v.patternMismatch) return inp.name === "phone" ? "Enter a 10-digit mobile number starting with 6–9." : inp.name === "pincode" ? "Enter a 6-digit PIN code." : `${label} doesn't look right.`;
    return inp.validationMessage;
  };
  $$(".field input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file]), .field select, .field textarea").forEach((inp) => {
    const field = inp.closest(".field");
    if (!field) return;
    if (!$(".ok-mark", field) && inp.tagName !== "TEXTAREA" && inp.type !== "password" && inp.tagName !== "SELECT") {
      const m = document.createElement("span"); m.className = "ok-mark";
      m.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M20 6 9 17l-5-5"/></svg>';
      field.appendChild(m);
    }
    const check = () => {
      const ok = inp.checkValidity();
      field.classList.toggle("valid", !!inp.value && ok);
      if (inp.value || inp.required) { field.classList.toggle("has-error", !ok); if (!inp.dataset.match) showLive(inp, ok ? "" : friendly(inp)); }
    };
    inp.addEventListener("blur", () => { if (inp.value) check(); });
    inp.addEventListener("input", () => { if (field.classList.contains("has-error") || field.classList.contains("valid")) check(); });
    if (inp.name === "phone" || inp.name === "pincode") inp.addEventListener("input", () => { inp.value = inp.value.replace(/\D/g, ""); });
  });
  $$("[data-counter]").forEach((ta) => {
    const max = parseInt(ta.dataset.counter, 10), c = document.createElement("span");
    c.className = "counter"; ta.parentNode.style.position = "relative"; ta.parentNode.appendChild(c);
    const upd = () => { const n = ta.value.length; c.textContent = `${n}/${max}`; c.className = "counter" + (n > max * 0.9 ? " bad" : n > max * 0.75 ? " warn" : ""); };
    ta.addEventListener("input", upd); upd();
  });

  // ---------------------------------------------------------------- photo dropzone with client-side checks
  $$("[data-dropzone]").forEach((dz) => {
    const input = $("input[type=file]", dz), max = parseFloat(dz.dataset.maxMb || 5), minPx = parseInt(dz.dataset.minPx || 200, 10);
    const err = $("[data-dz-error]", dz.closest(".field") || document);
    const fail = (m) => { input.value = ""; dz.classList.remove("has-img"); $(".preview", dz)?.remove(); if (err) err.textContent = m; };
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, () => dz.classList.remove("over")));
    input.addEventListener("change", () => {
      const f = input.files[0]; if (!f) return;
      if (err) err.textContent = "";
      if (!/^image\/(jpeg|png|webp)$/.test(f.type)) return fail("Only JPG, PNG or WEBP photos are allowed.");
      if (f.size > max * 1048576) return fail(`This photo is ${(f.size / 1048576).toFixed(1)} MB. The limit is ${max} MB.`);
      const url = URL.createObjectURL(f), img = new Image();
      img.onload = () => {
        if (Math.min(img.naturalWidth, img.naturalHeight) < minPx) return fail(`Photo is too small (${img.naturalWidth}×${img.naturalHeight}). Use at least ${minPx}px.`);
        $(".preview", dz)?.remove(); img.className = "preview"; dz.prepend(img); dz.classList.add("has-img");
      };
      img.onerror = () => fail("This file isn't a valid image.");
      img.src = url;
    });
  });

  // ---------------------------------------------------------------- multi-step wizard
  $$("[data-wizard]").forEach((form) => {
    const steps = $$(".wstep", form), bars = $$(".steps-bar .s", form);
    let cur = form.dataset.start !== undefined ? parseInt(form.dataset.start, 10) : Math.max(0, steps.findIndex((s) => $(".errors, .has-error", s)));
    const show = (i) => {
      steps.forEach((s, j) => s.classList.toggle("active", j === i));
      bars.forEach((b, j) => b.classList.toggle("on", j <= i));
      cur = i;
      const top = form.getBoundingClientRect().top + scrollY - 90;
      if (scrollY > top) scrollTo({ top, behavior: reduced ? "auto" : "smooth" });
      $$("[data-review]", form).forEach((el) => {
        const src = form.querySelector(`[name=${el.dataset.review}]`);
        if (!src) return;
        if (src.type === "radio") { const c = form.querySelector(`[name=${el.dataset.review}]:checked`); el.textContent = c ? (c.dataset.label || c.closest("label").innerText.trim().split("\n")[0]) : "—"; }
        else if (src.tagName === "SELECT") el.textContent = src.selectedIndex > 0 ? src.options[src.selectedIndex].text : "—";
        else el.textContent = src.value || "—";
      });
      const prev = $("[data-review-photo]", form), pimg = $(".dropzone .preview", form);
      if (prev && pimg) prev.src = pimg.src;
    };
    $$("[data-next]", form).forEach((b) => b.addEventListener("click", () => {
      const fields = $$("input, select, textarea", steps[cur]).filter((f) => f.type !== "hidden");
      const radios = new Set(fields.filter((f) => f.type === "radio" && f.required).map((f) => f.name));
      for (const name of radios) if (!form.querySelector(`[name=${name}]:checked`)) { SSToast("Please choose an option to continue.", "error"); return; }
      const bad = fields.find((f) => f.type !== "radio" && !f.checkValidity());
      if (bad) {
        bad.closest(".field")?.classList.add("has-error");
        if (bad.type === "file") SSToast("Please add a photo of the problem.", "error"); else { showLive(bad, friendly(bad)); bad.focus(); }
        return;
      }
      show(cur + 1);
    }));
    $$("[data-prev]", form).forEach((b) => b.addEventListener("click", () => show(cur - 1)));
    show(cur);
  });

  // ---------------------------------------------------------------- geolocation
  $$("[data-locate]").forEach((btn) => {
    const box = btn.closest(".loc-box"), frame = $(".map-frame"), label = $("[data-loc-text]");
    btn.addEventListener("click", () => {
      if (!navigator.geolocation) return SSToast("Your browser can't share location.", "error");
      btn.classList.add("loading");
      navigator.geolocation.getCurrentPosition((p) => {
        const lat = p.coords.latitude.toFixed(6), lng = p.coords.longitude.toFixed(6);
        $("#id_latitude").value = lat; $("#id_longitude").value = lng;
        btn.classList.remove("loading"); box && box.classList.add("ok");
        if (label) label.textContent = `Location added · ${lat}, ${lng} (±${Math.round(p.coords.accuracy)} m)`;
        if (frame) { const d = 0.004; frame.src = `https://www.openstreetmap.org/export/embed.html?bbox=${lng - d},${lat - d},${+lng + d},${+lat + d}&layer=mapnik&marker=${lat},${lng}`; frame.classList.add("show"); }
      }, (e) => {
        btn.classList.remove("loading");
        SSToast(e.code === 1 ? "Location permission was denied. You can still type the address." : "Couldn't get your location. Please type the address.", "error");
      }, { enableHighAccuracy: true, timeout: 12000 });
    });
  });

  // ---------------------------------------------------------------- upvote without reload
  $$("form[data-vote]").forEach((f) => f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const b = $("button", f), n = $("[data-n]", b);
    try {
      const r = await fetch(f.action, { method: "POST", body: new FormData(f), headers: { "x-requested-with": "fetch" } });
      const d = await r.json();
      if (!d.ok) return SSToast(d.message, "error");
      b.classList.toggle("on", d.on); if (n) n.textContent = d.count;
      b.classList.remove("bump"); void b.offsetWidth; b.classList.add("bump");
    } catch (err) { f.submit(); }
  }));

  // ---------------------------------------------------------------- admin: sidebar + command palette
  const side = $(".side"), menuBtn = $(".p-menu-btn");
  const setSide = (open) => { if (!side) return; side.classList.toggle("open", open); document.body.classList.toggle("side-open", open); };
  menuBtn && menuBtn.addEventListener("click", () => setSide(!side.classList.contains("open")));
  $$("[data-side-close]").forEach((b) => b.addEventListener("click", () => setSide(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setSide(false); });
  // Desktop: collapse the sidebar to an icon rail, remembered for next time.
  $$("[data-collapse]").forEach((b) => b.addEventListener("click", () => {
    if (innerWidth <= 1100) return setSide(false);
    const mini = document.documentElement.classList.toggle("side-mini");
    try { localStorage.setItem("ss-side", mini ? "mini" : "full"); } catch (e) {}
    setTimeout(() => window.Chart && Object.values(Chart.instances || {}).forEach((c) => c.resize()), 320);
  }));
  const pal = $(".palette-bg");
  if (pal) {
    const input = $("input", pal), items = $$(".items a", pal);
    let sel = 0;
    const visible = () => items.filter((a) => a.style.display !== "none");
    const mark = () => visible().forEach((a, i) => a.classList.toggle("sel", i === sel));
    const filter = () => {
      const q = input.value.trim().toLowerCase(); sel = 0;
      items.forEach((a) => a.style.display = !q || a.textContent.toLowerCase().includes(q) ? "" : "none");
      const go = $("[data-goto-code]", pal);
      if (go) go.style.display = /^ss-?\d{4}-?\d+$/i.test(q) || /^\d{1,5}$/.test(q) ? "" : "none";
      mark();
    };
    const open = () => { pal.classList.add("open"); input.value = ""; filter(); setTimeout(() => input.focus(), 20); };
    const close = () => pal.classList.remove("open");
    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); pal.classList.contains("open") ? close() : open(); }
      if (!pal.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(sel + 1, visible().length - 1); mark(); }
      if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(sel - 1, 0); mark(); }
      if (e.key === "Enter") {
        e.preventDefault();
        const q = input.value.trim().toUpperCase();
        if (/^\d{1,5}$/.test(q) || /^SS-?\d{4}-?\d+$/.test(q)) {
          const code = /^\d+$/.test(q) ? `SS-${new Date().getFullYear()}-${q.padStart(4, "0")}` : q.replace(/^SS-?(\d{4})-?(\d+)$/, "SS-$1-$2");
          location.href = pal.dataset.base + code + "/"; return;
        }
        const a = visible()[sel]; a && (location.href = a.href);
      }
    });
    input.addEventListener("input", filter);
    pal.addEventListener("click", (e) => { if (e.target === pal) close(); });
    $$("[data-palette]").forEach((b) => b.addEventListener("click", open));
  }

  // ---------------------------------------------------------------- charts theme
  if (window.Chart) {
    Chart.defaults.font.family = "'Instrument Sans', system-ui, sans-serif";
    Chart.defaults.color = "#6B7770";
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
    Chart.defaults.plugins.tooltip.backgroundColor = "#15211B";
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.scale.grid.color = "#F0EDE6";
    Chart.defaults.scale.border.display = false;
    Chart.defaults.animation.duration = 1100;
    Chart.defaults.animation.easing = "easeOutQuart";
  }
  // SSChart(canvas, config): builds the chart only when it scrolls into view, so it animates in front of the user.
  window.SSChart = (el, cfg) => {
    if (!el || !window.Chart) return;
    if (!("IntersectionObserver" in window) || reduced) return new Chart(el, cfg);
    let made = false;
    const make = () => { if (!made) { made = true; io.disconnect(); new Chart(el, cfg); } };
    const io = new IntersectionObserver((en) => { if (en[0].isIntersecting) make(); }, { threshold: 0.25 });
    io.observe(el);
    const r = el.getBoundingClientRect();
    if (r.top < innerHeight && r.bottom > 0) setTimeout(make, 250);
    addEventListener("scroll", function chk() {
      const b = el.getBoundingClientRect();
      if (b.top < innerHeight * 0.85 && b.bottom > 0) { removeEventListener("scroll", chk); make(); }
    }, { passive: true });
  };

  // ---------------------------------------------------------------- PWA
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
  }
})();
