(function() {
  var lightThemeStartHour = 6;
  var darkThemeStartHour = 18;
  var toggle = document.getElementById('site-theme-toggle');

  function getThemeForTime(date) {
    var hour = date.getHours();
    return hour >= lightThemeStartHour && hour < darkThemeStartHour ? 'light' : 'dark';
  }

  function updateToggle(theme) {
    if (!toggle) return;

    var nextThemeName = theme === 'dark' ? 'day mode' : 'night mode';
    toggle.setAttribute('aria-label', 'Switch to ' + nextThemeName);
    toggle.title = 'Switch to ' + nextThemeName;
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
}());
