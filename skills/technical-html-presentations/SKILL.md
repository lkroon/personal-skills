---
name: technical-html-presentations
description: Creates and updates repository-grounded technical presentations as self-contained HTML while preserving visual language, navigation, responsive layout, speaker notes, and print behavior. Use whenever users mention technical slide decks, architecture or design-review presentations, presentation HTML, docs/presentations files, adding or removing slides, or turning specs and fixture evidence into a browser-presentable narrative.
compatibility: Requires Python 3 for the bundled deck validator.
metadata:
  source: /home/lkroon/.agents/skills/technical-html-presentations
  migration-date: "2026-07-29"
---

# Technical HTML Presentations

## Objective

Build a presentation whose claims are traceable, whose narrative supports a decision, and whose HTML remains usable offline on desktop, mobile, and print.

## Start With Evidence

1. Read the existing deck, relevant specs, source, fixtures, executable prototypes, and recent history before editing.
2. Record the source of displayed values and distinguish current behavior, proposed behavior, and measured evidence.
3. Qualify local timings and environment-specific benchmarks.
4. Resolve ambiguous terminology before it reaches slide copy.

If the deck explains a non-obvious transformation, invoke `worked-example-documentation` before drafting those slides. Carry a small verified fixture through every intermediate state instead of jumping from input to output.

## Narrative

- Give each slide one primary takeaway.
- Prefer a problem → evidence → mechanism → worked example → outcome → decision sequence.
- Use concrete tables and diagrams instead of dense prose.
- Add slides when an intermediate step is necessary for comprehension; do not compress a workflow merely to preserve slide count.
- Keep source references and speaker notes close to the slide they support.

## Existing Decks

Preserve the established typography, colors, components, controls, and visual language. Make the smallest coherent change. When inserting or removing slides, update visible slide hints, the initial counter, initial progress width, speaker-note count, and any static references to total slides.

## New Self-Contained Decks

Use semantic `<section class="slide">` elements, embedded CSS and JavaScript, keyboard and clickable navigation, touch navigation where appropriate, exactly one `<aside class="speaker-notes">` per slide, responsive layouts, and one-slide-per-page print styles. Include exactly one `.progress` element and initialize it with a standalone `.progress { ... width: N%; ... }` rule, where `N` equals `100 / slide count`. Avoid CDNs, external fonts, external images, frameworks, and build steps unless requested.

## Layout Rules

- Keep text readable in a single desktop viewport.
- Put wide tables in horizontal overflow containers on narrow screens.
- Prefer CSS/HTML diagrams or inline SVG.
- Preserve logical reading order and accessible control labels.
- Make navigation and progress updates derive the runtime slide total from the DOM.

## Verification

Check displayed facts against their sources. Open or parse the deck, navigate to every slide, inspect narrow layouts, and check print behavior when browser tooling is available. From this skill's base directory, always run:

```bash
python3 scripts/validate_deck.py path/to/deck.html
```

Validation rejects external resource dependencies by default. Only when the user explicitly requested external resources, pass the opt-out:

Ordinary external `<a href>` references remain allowed because they do not load deck resources.

```bash
python3 scripts/validate_deck.py --allow-external path/to/deck.html
```

Fix every reported structural, metadata, progress, speaker-note, or external-dependency error before completion. Report browser checks that could not be performed rather than implying they passed.
