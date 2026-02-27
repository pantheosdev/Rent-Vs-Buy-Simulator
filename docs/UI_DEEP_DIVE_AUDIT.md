# UI Deep Dive Audit (Premium polish + performance + UX)

This audit is based on a code-level review of the Streamlit UI implementation and theme system.

## Executive summary

- The app has strong ambition in visual styling, but the UI stack is currently **overridden in many layers** (Python monkey-patches, huge CSS, and runtime JS listeners), which increases visual drift risk and perceived lag.
- The most impactful upgrades are: **reduce CSS/JS complexity**, **move to a tokenized design system**, **improve accessibility defaults**, and **decompose the monolithic page flow into smaller cached/render-isolated components**.

## Findings (60)

| # | Category | Finding | Why it matters | Premium/pro fix |
|---:|---|---|---|---|
| 1 | Typography | Global base font size is forced to 13px. | Reads small on many laptops and hurts perceived quality. | Raise to 14–16px scale with responsive `clamp()`. |
| 2 | Typography | Line-height is globally set to 1.35. | Dense text blocks feel cramped and less elegant. | Use 1.45–1.6 for body/caption text tiers. |
| 3 | Typography | There are multiple competing font declarations (`--rbv-font-sans`, `--rbv-font`). | Increases inconsistency and makes debugging expensive. | Keep one canonical font token set. |
| 4 | Typography | Google font is imported through CSS `@import`. | `@import` can delay text rendering and increase FOIT/FOUT risk. | Preconnect and use `<link>` strategy with fallback stack. |
| 5 | Accessibility | Heavy use of ALL CAPS-like visual treatment in some headers and badges. | Reduces readability and appears shouty. | Reserve caps for tiny labels only; prefer sentence case. |
| 6 | Accessibility | Bright text color (`#F8FAFC`) is forced for many elements including labels/spans. | Removes hierarchy and causes visual glare on dark backgrounds. | Use semantic text tiers (primary/secondary/tertiary). |
| 7 | Accessibility | Sidebar built-in help icons are fully hidden. | Removes discoverable guidance and can hurt keyboard/screen-reader users. | Keep accessible help affordance with consistent iconography. |
| 8 | Accessibility | Radio inputs are hidden via CSS and restyled labels used as tabs. | Can create keyboard/focus inconsistencies and fragile semantics. | Use native tabs component with accessible roles/states. |
| 9 | Accessibility | Many rules depend on `:has(input:checked)`. | Browser support/perf can vary; can cause inconsistent tab state styling. | Add class-based state hook from Python or JS once. |
| 10 | Accessibility | Tooltip behavior relies on hover for display. | Hover-only help is weak for touch and keyboard users. | Add click/focus toggles with escape-close behavior. |
| 11 | Visual consistency | CSS uses a very large number of `!important` overrides. | Hard to maintain; tiny changes create regressions elsewhere. | Reduce specificity and adopt layered token/utility architecture. |
| 12 | Visual consistency | Same tooltip selectors are overridden multiple times. | Conflicting rules increase flicker and unpredictability. | Consolidate tooltip styles into one source of truth. |
| 13 | Visual consistency | Sidebar width is hard-coded to 340px desktop. | Can feel cramped or oversized depending on viewport. | Use responsive width clamp (`min/max`) and user-resizable option. |
| 14 | Visual consistency | Border/shadow strengths vary heavily between cards, banners, and tooltips. | Surface system feels mismatched instead of premium cohesive. | Define elevation scale (e.g., 3 shadow levels) and reuse. |
| 15 | Visual consistency | Color substitutions are regex-based across raw CSS. | Dynamic replacement is brittle and hard to reason about. | Replace with CSS variables and avoid string regex patching. |
| 16 | Visual consistency | Legacy palette mappings still exist for many historical colors. | Signals debt; can leak old color accents accidentally. | Remove stale color aliases after migration. |
| 17 | Visual consistency | Multiple tooltip z-index values (`100000`, `1000000`, etc.). | Creates stacking chaos and difficult bug triage. | Use standardized z-index tokens. |
| 18 | Visual consistency | Inline spacing divs (`<div style="height:...">`) are frequent. | Creates inconsistent rhythm and harder layout tuning. | Replace with spacing utility classes/components. |
| 19 | Performance | Global CSS is injected every rerun by design. | Increases DOM bloat and style recalculation frequency. | Cache a versioned style tag and update only when changed. |
| 20 | Performance | A large script runs `setInterval(update, 500)` continuously. | Reflow polling every 500ms can cause jank and battery drain. | Replace with `ResizeObserver` + targeted event hooks. |
| 21 | Performance | Additional `resize` + `scroll` listeners are attached globally. | Frequent callbacks add layout recalculations on interaction. | Debounce/throttle and scope listeners narrowly. |
| 22 | Performance | Tooltip auto-flip repeatedly measures DOM on hover/focus. | `getBoundingClientRect()` loops can stutter on dense pages. | Compute once per tooltip open and cache measurements. |
| 23 | Performance | Extensive querySelector usage from injected JS each update cycle. | Adds overhead and scales poorly with page complexity. | Cache nodes and invalidate only on mutation changes. |
| 24 | Performance | Heavy use of HTML-in-Markdown rendering throughout app. | Large HTML fragments slow reruns and reduce composability. | Convert repeated fragments into reusable render helpers/components. |
| 25 | Performance | Monolithic single-file app (`app.py`) is very large. | Slower iteration, harder profiling, more accidental rerenders. | Split into feature modules with isolated render functions. |
| 26 | Performance | Widget monkey-patching wraps most Streamlit controls globally. | Adds indirection and risk for Streamlit version drift. | Use explicit wrapper helpers only where necessary. |
| 27 | Performance | Session caches use coarse `cache.clear()` eviction. | Causes sudden recompute spikes and inconsistent responsiveness. | Use LRU/TTL eviction rather than full clear. |
| 28 | Performance | Cache soft caps are high and broad (`max_items=5000`). | Memory growth can still feel laggy on long sessions. | Add per-cache sizing based on object weight. |
| 29 | Performance | Repeated expensive formatting/tables in same rerun path. | Increases rerun latency especially with large dataframes. | Memoize view-model transformations separately from rendering. |
| 30 | Performance | Plotly charts are repeatedly themed per render call. | Extra layout mutation work every rerun. | Predefine figure template and minimize per-chart mutations. |
| 31 | UX clarity | Sidebar is packed with many collapsed/expanded sections. | Cognitive load is high for first-time users. | Introduce progressive onboarding and “basic vs advanced” modes. |
| 32 | UX clarity | Many options appear both in sidebars and main content contexts. | Users can lose where to edit what. | Enforce strict information architecture by task stage. |
| 33 | UX clarity | Several hints are long and technical for casual users. | Slows comprehension and adds decision fatigue. | Rewrite into short actionable microcopy with optional details. |
| 34 | UX clarity | Mode-specific behavior is scattered across controls and notes. | Hard to predict outputs and trust results quickly. | Add explicit mode summary card pinned near Run/Results. |
| 35 | UX clarity | Custom city preset filters have many nested controls. | Good power feature, but heavy for quick starts. | Provide “Top 8 starter presets” quick chips first. |
| 36 | UX clarity | Important compare features are inside collapsible preview areas. | Advanced value can be missed by users. | Surface compare CTA prominently in results header. |
| 37 | UX clarity | Multiple warning/info blocks compete visually. | User attention is fragmented. | Apply severity hierarchy (info/warn/error tokens + spacing). |
| 38 | UX clarity | Dense financial tables can feel intimidating in dark mode. | Harder scanability lowers confidence in insights. | Add zebra stripes, sticky headers, and row grouping. |
| 39 | UX clarity | Some radios have intentionally blank labels. | Can reduce accessibility and context in screen readers. | Keep semantic labels and visually hide with accessible CSS pattern. |
| 40 | UX clarity | Tooltips carry critical explanations, not just supportive hints. | Hidden knowledge creates discoverability gap. | Promote critical content into inline helper text. |
| 41 | Interaction quality | Tooltip and selectbox behavior depends on custom DOM scripts. | Fragile across Streamlit/BaseWeb updates. | Prefer native component APIs before JS interception. |
| 42 | Interaction quality | Select arrow close workaround dispatches synthetic Escape. | Can create unexpected close behavior in edge cases. | Replace with controlled dropdown components or upstream fix. |
| 43 | Interaction quality | “Stop current run” is soft-cancel via rerun flag. | Users may still feel app is unresponsive during heavy compute. | Add true chunked compute checkpoints + progress cancel points. |
| 44 | Interaction quality | Long-running analyses are mixed into same page render loop. | UI can freeze while compute dominates. | Move heavy compute to async/background worker abstraction. |
| 45 | Interaction quality | Some expanders default open (e.g., key simulation sections). | Creates long initial scroll and visual clutter. | Start with concise summary, open details on demand. |
| 46 | Interaction quality | High density of sliders and number inputs in grids. | Inputs feel crowded and error-prone. | Increase vertical rhythm and group by decision intent. |
| 47 | Visual polish | Shadows are often very strong and dark. | Can look “game UI” rather than professional fintech. | Tone down blur/opacity; rely on contrast and spacing. |
| 48 | Visual polish | Accent gradients are used in multiple high-contrast areas. | Too many focal points reduce premium restraint. | Reserve accent gradients for top 1–2 hero elements. |
| 49 | Visual polish | Sidebar and main surfaces use different dark palettes (`#1A1A1A` vs navy). | Mixed neutrals can look disjointed. | Harmonize neutrals through single neutral ramp. |
| 50 | Visual polish | Label rows and tooltip icons are custom-built extensively. | Reinventing primitives increases inconsistency risk. | Standardize with a compact design-system component set. |
| 51 | Reliability | Broad `try/except: pass` patterns are common in UI plumbing. | Silent failures hide rendering defects and regressions. | Capture diagnostics with structured logging + visible debug mode. |
| 52 | Reliability | Startup import fallbacks keep app running with partial functionality. | Good resilience, but hidden degradation may confuse users. | Show explicit degraded-mode banner with impacted features list. |
| 53 | Reliability | CSS depends heavily on `data-testid` selectors. | `data-testid` can change across Streamlit versions. | Prefer stable semantic selectors or wrapper classes. |
| 54 | Reliability | Extensive JS/CSS manipulations target BaseWeb internals. | Library internals are volatile and can break unexpectedly. | Minimize internals targeting; encapsulate in compatibility layer. |
| 55 | Maintainability | UI behavior, engine controls, diagnostics, and exports are interwoven. | Hard to reason about side effects and regressions. | Separate presenter layer from simulation orchestration. |
| 56 | Maintainability | Many inline HTML snippets fragment style ownership. | Designers/devs cannot quickly audit component consistency. | Move repeated UI blocks into typed helper functions/components. |
| 57 | Maintainability | Theme file is extremely long and mixes old/new comment epochs. | Hard onboarding and slower bug-fix throughput. | Split theme into tokens/layout/components/overrides files. |
| 58 | Maintainability | Multiple “hotfix” and version-note CSS sections coexist. | Technical debt accumulates and conflicts grow over time. | Introduce deprecation pass per release to remove superseded blocks. |
| 59 | Premium feel | Dense settings-first experience can feel tool-like, not product-like. | Professional users still value guided defaults and narrative. | Add scenario stories/templates with one-click apply. |
| 60 | Premium feel | Result presentation prioritizes breadth over storytelling. | Users may miss decisive insights despite rich data. | Add executive summary panel with 3 key takeaways + confidence. |

## Priority roadmap

1. **Performance first (Week 1–2):** remove polling interval layout script, throttle observers, reduce CSS reinjection churn.
2. **Design system hardening (Week 2–3):** tokenize typography/color/elevation/spacing; eliminate regex palette patching.
3. **UX simplification (Week 3–4):** split basic vs advanced controls; move critical guidance inline.
4. **Maintainability (Week 4+):** modularize `app.py` UI into feature sections and component helpers.

## Suggested KPIs to track improvements

- Median Streamlit rerun time (p50/p95).
- CSS/JS payload size injected per rerun.
- Number of `!important` declarations.
- Accessibility score (axe or Lighthouse in browser-mode harness).
- First meaningful interaction time on a cold session.
