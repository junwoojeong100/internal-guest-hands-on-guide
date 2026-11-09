(() => {
  "use strict";
  const toc = document.getElementById("toc");
  const sections = [...document.querySelectorAll(".observed-section")];
  if (!toc || !sections.length) throw new Error("Missing guide navigation or sections.");
  const topbar = document.querySelector(".topbar");
  if (topbar) {
    const syncTopbarHeight = () => document.documentElement.style.setProperty("--topbar-h", `${topbar.offsetHeight}px`);
    syncTopbarHeight();
    new ResizeObserver(syncTopbarHeight).observe(topbar);
  }
  const activeLink = id => {
    toc.querySelectorAll("a").forEach(link => {
      const active = link.hash === `#${id}`;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  };
  const observer = new IntersectionObserver(entries => {
    entries.filter(entry => entry.isIntersecting).forEach(entry => activeLink(entry.target.id));
  }, {rootMargin:"-15% 0px -65% 0px",threshold:0});
  sections.forEach(section => observer.observe(section));
  activeLink(sections[0].id);

  // Deep links: open a closed <details> that contains the target, then keep the target aligned
  // while lazy images shift the layout, until the reader scrolls or interacts.
  const hashTarget = () => {
    let id;
    try {
      id = decodeURIComponent(window.location.hash.slice(1));
    } catch (error) {
      if (error instanceof URIError) return null;
      throw error;
    }
    return id ? document.getElementById(id) : null;
  };
  let stopAligning = () => {};
  const showHashTarget = () => {
    stopAligning();
    const target = hashTarget();
    if (!target) return;
    for (let node = target; node; node = node.parentElement) {
      if (node instanceof HTMLDetailsElement) node.open = true;
    }
    const interactions = ["wheel", "touchstart", "keydown", "mousedown"];
    let initialReport = true;
    const observer = new ResizeObserver(() => {
      if (initialReport) {
        initialReport = false;
        return;
      }
      target.scrollIntoView({block: "start", behavior: "instant"});
    });
    const stop = () => {
      observer.disconnect();
      window.clearTimeout(timer);
      interactions.forEach(type => window.removeEventListener(type, stop));
      if (stopAligning === stop) stopAligning = () => {};
    };
    const timer = window.setTimeout(stop, 5000);
    stopAligning = stop;
    interactions.forEach(type => window.addEventListener(type, stop, {passive: true}));
    observer.observe(document.body);
  };
  window.addEventListener("hashchange", showHashTarget);
  showHashTarget();
  window.__navigationReady = true;
})();
