/* site.js — shared behaviour for every page
   ---------------------------------------------------------
   Everything here used to be copy-pasted into each HTML file.
   Keep it here so a fix lands once instead of five times.

     · Footer "last updated" stamp
     · Theme toggle
     · Document modal (CV, thesis summary, …)
     · Abstract toggles          (research.html)
     · BibTeX cite buttons       (research.html)
     · Scroll-to-top button
     · Mobile hamburger menu
   --------------------------------------------------------- */
(function () {
    'use strict';

    /* Single source of truth for the footer date — edit this one line. */
    var SITE_UPDATED = 'August 2026';

    /* Fallback document shown by triggers that don't name their own. */
    var CV_SRC = 'https://drive.google.com/file/d/14yQ4v4fANxc674NiDEIoY8fFCZTq3TPw/preview';
    var CV_TITLE = 'Curriculum Vitae';

    /* ── Footer "last updated" stamp ───────────────────────── */
    document.querySelectorAll('.footer-updated').forEach(function (el) {
        el.textContent = 'Updated ' + SITE_UPDATED;
    });

    /* ── Theme toggle ──────────────────────────────────────── */
    var themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        var root = document.documentElement;
        themeToggle.addEventListener('click', function () {
            var isDark = root.getAttribute('data-theme') === 'dark'
                || (!root.hasAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
            var next = isDark ? 'light' : 'dark';
            root.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        });
    }

    /* ── Document modal ────────────────────────────────────── */
    /* Triggers: [data-cv-trigger] opens the CV; [data-modal-trigger]
       opens whatever data-modal-src / data-modal-title name. */
    var modalTriggers = document.querySelectorAll('[data-cv-trigger], [data-modal-trigger]');

    if (modalTriggers.length) {
        var backdrop = document.createElement('div');
        backdrop.className = 'cv-backdrop';
        backdrop.setAttribute('data-cv-close', '');

        var modal = document.createElement('div');
        modal.className = 'cv-modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', 'cv-modal-title');
        modal.setAttribute('aria-hidden', 'true');
        modal.innerHTML =
            '<div class="cv-modal-header">'
            + '<h2 class="cv-modal-title" id="cv-modal-title"></h2>'
            + '<button class="cv-close" type="button" data-cv-close>Close</button>'
            + '</div>'
            + '<div class="cv-modal-body"><iframe allowfullscreen loading="lazy"></iframe></div>';

        document.body.appendChild(backdrop);
        document.body.appendChild(modal);

        var modalTitle = modal.querySelector('.cv-modal-title');
        var modalFrame = modal.querySelector('iframe');
        var closeBtn = modal.querySelector('.cv-close');
        var lastFocused = null;

        var openModal = function (trigger) {
            var src = trigger.getAttribute('data-modal-src') || CV_SRC;
            var title = trigger.getAttribute('data-modal-title') || CV_TITLE;

            /* Only reload the iframe when the document actually changes. */
            if (modalFrame.getAttribute('src') !== src) {
                modalFrame.setAttribute('src', src);
            }
            modalFrame.title = title;
            modalTitle.textContent = title;

            lastFocused = document.activeElement;
            document.body.classList.add('cv-modal-open');
            modal.setAttribute('aria-hidden', 'false');
            closeBtn.focus();
        };

        var closeModal = function () {
            document.body.classList.remove('cv-modal-open');
            modal.setAttribute('aria-hidden', 'true');
            if (lastFocused && typeof lastFocused.focus === 'function') {
                lastFocused.focus();
            }
            lastFocused = null;
        };

        modalTriggers.forEach(function (trigger) {
            trigger.addEventListener('click', function (event) {
                event.preventDefault();
                openModal(trigger);
            });
        });

        document.querySelectorAll('[data-cv-close]').forEach(function (el) {
            el.addEventListener('click', closeModal);
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && document.body.classList.contains('cv-modal-open')) {
                closeModal();
            }
        });
    }

    /* ── Abstract toggles ──────────────────────────────────── */
    document.querySelectorAll('[data-abstract-toggle]').forEach(function (btn) {
        var body = document.getElementById(btn.getAttribute('data-abstract-toggle'));
        if (!body) return;

        /* Set the initial state here rather than on first click, so screen
           readers don't start out being told the abstract is expanded. */
        btn.setAttribute('aria-expanded', 'false');
        btn.setAttribute('aria-controls', body.id);

        btn.addEventListener('click', function () {
            var isOpen = !body.classList.contains('open');
            body.classList.toggle('open', isOpen);
            btn.classList.toggle('open', isOpen);
            btn.setAttribute('aria-expanded', String(isOpen));
        });
    });

    /* ── BibTeX cite buttons ───────────────────────────────── */
    function flashCopied(btn) {
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(function () {
            btn.textContent = 'Cite';
            btn.classList.remove('copied');
        }, 2000);
    }

    function copyFallback(text, done) {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
        document.body.appendChild(ta);
        ta.select();
        try {
            document.execCommand('copy');
            done();
        } catch (e) { /* clipboard unavailable — leave the button alone */ }
        document.body.removeChild(ta);
    }

    document.querySelectorAll('.cite-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var bib = btn.getAttribute('data-bib') || '';
            var done = function () { flashCopied(btn); };

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(bib).then(done, function () {
                    copyFallback(bib, done);
                });
            } else {
                copyFallback(bib, done);
            }
        });
    });

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
    var nav = header ? header.querySelector('nav') : null;

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
            var card = btn.closest('.statement-card');
            var full = card ? card.querySelector('.statement-full') : null;
            if (!full) return;
            var isOpen = full.classList.toggle('open');
            btn.textContent = isOpen ? 'Show less ↑' : 'Read full statement →';
        });
    });

})();
