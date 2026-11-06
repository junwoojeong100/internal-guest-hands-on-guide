(() => {
  "use strict";
  const toc = document.getElementById("toc");
  const sections = [...document.querySelectorAll(".observed-section")];
  if (!toc || !sections.length) throw new Error("Missing guide navigation or sections.");
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
  window.__navigationReady = true;
})();
