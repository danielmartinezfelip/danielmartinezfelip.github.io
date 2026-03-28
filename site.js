/* site.js — shared enhancements
   #11 Reading progress bar
   #12 Scroll-to-top button
   #17 Mobile hamburger menu
   --------------------------------------------------------- */
(function () {
    'use strict';

    /* ── Reading progress bar ──────────────────────────────── */
    var progress = document.createElement('div');
    progress.className = 'reading-progress';
    document.body.insertBefore(progress, document.body.firstChild);

    function updateProgress() {
        var total = document.documentElement.scrollHeight - window.innerHeight;
        progress.style.width = (total > 0 ? (window.scrollY / total) * 100 : 0) + '%';
    }
    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();

    /* ── Scroll-to-top button ──────────────────────────────── */
    var scrollBtn = document.createElement('button');
    scrollBtn.className = 'scroll-top-btn';
    scrollBtn.setAttribute('aria-label', 'Scroll to top');
    scrollBtn.setAttribute('title', 'Scroll to top');
    scrollBtn.textContent = '↑';
    document.body.appendChild(scrollBtn);

    window.addEventListener('scroll', function () {
        scrollBtn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    scrollBtn.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    /* ── Mobile hamburger menu ─────────────────────────────── */
    var header = document.querySelector('header');
    var nav    = header ? header.querySelector('nav') : null;

    if (header && nav) {
        nav.classList.add('nav-collapsible');
        nav.id = nav.id || 'site-nav';

        var hamburger = document.createElement('button');
        hamburger.className = 'hamburger';
        hamburger.setAttribute('aria-label', 'Toggle navigation');
        hamburger.setAttribute('aria-expanded', 'false');
        hamburger.setAttribute('aria-controls', nav.id);
        hamburger.innerHTML =
            '<span class="hamburger-line"></span>' +
            '<span class="hamburger-line"></span>' +
            '<span class="hamburger-line"></span>';
        header.insertBefore(hamburger, nav);

        hamburger.addEventListener('click', function () {
            var isOpen = nav.classList.toggle('open');
            hamburger.classList.toggle('open', isOpen);
            hamburger.setAttribute('aria-expanded', String(isOpen));
        });

        /* Close when a nav link is tapped on mobile */
        nav.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                nav.classList.remove('open');
                hamburger.classList.remove('open');
                hamburger.setAttribute('aria-expanded', 'false');
            });
        });
    }

    /* ── Statement snippet toggles ─────────────────────────── */
    document.querySelectorAll('.statement-more-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var full = btn.closest('.statement-card').querySelector('.statement-full');
            if (!full) return;
            var isOpen = full.classList.toggle('open');
            btn.textContent = isOpen ? 'Show less ↑' : 'Read full statement →';
        });
    });

})();
