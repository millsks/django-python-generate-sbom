/*
 * Light/dark theme toggle (Story 21.3, AC #6).
 *
 * Carries over ThemeModeProvider.tsx's behaviour exactly: the choice persists under the
 * SAME `theme-mode` localStorage key (so a user's existing preference survives the move
 * off the SPA), and with no stored choice the OS `prefers-color-scheme` decides.
 *
 * The initial resolution does NOT happen here — an inline script in base.html's <head>
 * does it before the stylesheet paints, which is what prevents a flash of the wrong
 * theme. This file only handles the toggle button and keeps the icon in sync.
 */
(function () {
  'use strict'

  var STORAGE_KEY = 'theme-mode'
  var root = document.documentElement

  function currentMode() {
    return root.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light'
  }

  // Show the icon for the mode the button would switch TO, matching the SPA's tooltip
  // ("Switch to light" / "Switch to dark").
  function syncIcons() {
    var dark = currentMode() === 'dark'
    var toLight = document.querySelector('[data-theme-icon-dark]')
    var toDark = document.querySelector('[data-theme-icon-light]')
    if (toLight) toLight.hidden = !dark
    if (toDark) toDark.hidden = dark
  }

  function apply(mode) {
    root.setAttribute('data-bs-theme', mode)
    try {
      localStorage.setItem(STORAGE_KEY, mode)
    } catch (e) {
      /* localStorage unavailable (private mode): the toggle still works for this page. */
    }
    syncIcons()
  }

  var button = document.getElementById('theme-toggle')
  if (button) {
    button.addEventListener('click', function () {
      apply(currentMode() === 'dark' ? 'light' : 'dark')
    })
  }

  // Follow the OS while the user has made no explicit choice.
  try {
    var query = window.matchMedia('(prefers-color-scheme: dark)')
    query.addEventListener('change', function (event) {
      var stored = localStorage.getItem(STORAGE_KEY)
      if (stored !== 'light' && stored !== 'dark') {
        root.setAttribute('data-bs-theme', event.matches ? 'dark' : 'light')
        syncIcons()
      }
    })
  } catch (e) {
    /* matchMedia unsupported: the stored/default theme still applies. */
  }

  syncIcons()
})()
