/* Animated "working" dots for the job progress list (Story 22.20).
 *
 * Three things this has to survive, each of which broke a previous version:
 *
 * 1. **The five-second htmx swap.** The progress fragment is replaced wholesale, so any state
 *    kept in the DOM restarts. The counter therefore lives here, keyed by task.
 * 2. **The gap after that swap.** The replacement markup carries an EMPTY span, so the dots
 *    blanked until the next one-second tick — seen as "1 to 5 dots, then disappear, then back
 *    for 6 through 10", the 5 being the poll interval. Hence `paint()` on `htmx:afterSwap`:
 *    the count is re-rendered immediately, without advancing it.
 * 3. **Rendering nothing.** A zero state blanks the line for a second every cycle, so the
 *    sequence runs 1..10 and never 0.
 *
 * The cycle is a plain 1..10 and straight back to 1 — one second per length, no pause at the
 * end. A dwell on the tenth dot was tried and read as a stall before the restart.
 */
(function () {
  "use strict";

  var MAX_DOTS = 10;
  var steps = {};

  function dots(count) {
    var out = [];
    for (var i = 0; i < count; i++) {
      out.push(".");
    }
    return out.join(" ");
  }

  function render(advance) {
    var nodes = document.querySelectorAll("[data-task-dots]");
    var live = {};

    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      var key = node.getAttribute("data-task-key") || String(i);
      var step = steps[key];

      if (step === undefined) {
        step = 0; // a task appearing for the first time starts at one dot
      } else if (advance) {
        step = (step + 1) % MAX_DOTS;
      }

      steps[key] = step;
      live[key] = true;
      node.textContent = dots(step + 1);
    }

    if (!advance) {
      return; // a repaint must not discard counters for rows mid-swap
    }

    // Forget tasks that have finished, so a restarted one begins at one rather than resuming.
    for (var tracked in steps) {
      if (Object.prototype.hasOwnProperty.call(steps, tracked) && !live[tracked]) {
        delete steps[tracked];
      }
    }
  }

  function start() {
    render(false);
    window.setInterval(function () {
      render(true);
    }, 1000);
    // htmx replaces the progress fragment every five seconds; repaint the moment it does so the
    // dots never blank between the swap and the next tick.
    document.body.addEventListener("htmx:afterSwap", function () {
      render(false);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
