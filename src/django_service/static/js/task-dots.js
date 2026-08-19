/* Animated "working" dots for the job progress list (Story 22.20).
 *
 * The counter lives HERE, in a module-level map keyed by task, rather than being derived from
 * each task's start time. Deriving it from elapsed time looked elegant and read badly: a task
 * that had already been running for six seconds when its row first appeared started at six
 * dots, several tasks running at once each showed a different count, and client/server clock
 * skew shifted the whole thing — so the dots appeared to jump rather than count.
 *
 * The cycle is 1 through 10 and back to 1 — deliberately not 0 through 10. A zero state renders
 * as nothing at all, and for one second per cycle the dots simply vanish and then come back,
 * which reads as a glitch rather than as counting.
 *
 * It survives htmx's five-second swap of the progress fragment because it lives in this script,
 * which sits outside that fragment — a counter stored in the DOM would reset on every swap. A
 * task appearing for the first time has no entry yet, so it starts at one.
 */
(function () {
  "use strict";

  var MAX_DOTS = 10;
  var counters = {};

  function dots(count) {
    var out = [];
    for (var i = 0; i < count; i++) {
      out.push(".");
    }
    return out.join(" ");
  }

  function tick() {
    var nodes = document.querySelectorAll("[data-task-dots]");
    var live = {};

    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      var key = node.getAttribute("data-task-key") || String(i);
      var next = counters[key] === undefined ? 1 : (counters[key] % MAX_DOTS) + 1;
      counters[key] = next;
      live[key] = true;
      node.textContent = dots(next);
    }

    // Drop counters for tasks that have finished, so if one is ever restarted it begins at one
    // rather than resuming a stale count.
    for (var tracked in counters) {
      if (Object.prototype.hasOwnProperty.call(counters, tracked) && !live[tracked]) {
        delete counters[tracked];
      }
    }
  }

  function start() {
    tick();
    window.setInterval(tick, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
