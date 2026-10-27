(function() {
  var lightThemeStartHour = 6;
  var darkThemeStartHour = 18;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ----- Day / night theme -----
  var toggle = document.getElementById('site-theme-toggle');

  function getThemeForTime(date) {
    var hour = date.getHours();
    return hour >= lightThemeStartHour && hour < darkThemeStartHour ? 'light' : 'dark';
  }

  function updateToggle(theme) {
    if (!toggle) return;

    var nextThemeName = theme === 'dark' ? 'Day mode' : 'Night mode';
    toggle.setAttribute('aria-label', 'Switch to ' + nextThemeName.toLowerCase());
    toggle.title = 'Switch to ' + nextThemeName.toLowerCase();
    var label = toggle.querySelector('.site-theme-toggle__label');
    if (label) label.textContent = nextThemeName;
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    updateToggle(theme);
  }

  if (!document.documentElement.getAttribute('data-theme')) {
    applyTheme(getThemeForTime(new Date()));
  } else {
    updateToggle(document.documentElement.getAttribute('data-theme'));
  }

  if (toggle) {
    toggle.addEventListener('click', function() {
      var currentTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });
  }

  // ----- Sidebar: highlight the section currently in view -----
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.nav-link[data-section]'));
  var sections = navLinks
    .map(function(link) { return document.getElementById(link.getAttribute('data-section')); })
    .filter(Boolean);

  function setActiveLink(id) {
    navLinks.forEach(function(link) {
      var isActive = link.getAttribute('data-section') === id;
      link.classList.toggle('active', isActive);
      if (isActive) {
        link.setAttribute('aria-current', 'location');
      } else {
        link.removeAttribute('aria-current');
      }
    });
  }

  function updateActiveSection() {
    if (!sections.length) return;

    var current = sections[0].id;
    var threshold = window.innerHeight * 0.3;
    sections.forEach(function(section) {
      if (section.getBoundingClientRect().top <= threshold) current = section.id;
    });

    var atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
    if (atBottom) current = sections[sections.length - 1].id;

    setActiveLink(current);
  }

  if (sections.length) {
    var ticking = false;
    window.addEventListener('scroll', function() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function() {
        updateActiveSection();
        ticking = false;
      });
    }, { passive: true });
    window.addEventListener('resize', updateActiveSection);
    updateActiveSection();
  }

  // ----- News ticker: loop the list upwards, pause on hover / focus -----
  var secondsPerItem = 3.5;

  Array.prototype.forEach.call(document.querySelectorAll('[data-news-ticker]'), function(ticker) {
    var list = ticker.querySelector('.news-list');
    if (!list || reduceMotion) return;

    var items = Array.prototype.slice.call(list.children);
    if (!items.length || list.scrollHeight <= ticker.clientHeight) return;

    // A second copy of the items makes the loop seamless; it is hidden from
    // assistive technology and keyboard focus.
    items.forEach(function(item) {
      var clone = item.cloneNode(true);
      clone.setAttribute('aria-hidden', 'true');
      Array.prototype.forEach.call(clone.querySelectorAll('a'), function(link) {
        link.setAttribute('tabindex', '-1');
      });
      list.appendChild(clone);
    });

    ticker.style.setProperty('--news-duration', (items.length * secondsPerItem) + 's');
    ticker.classList.add('is-animated');
  });
}());
