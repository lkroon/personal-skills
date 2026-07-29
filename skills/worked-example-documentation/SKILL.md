---
name: worked-example-documentation
description: Builds verified, end-to-end worked examples for technical documentation by tracing real records through every intermediate representation. Use whenever docs, ADRs, specs, notebooks, or presentations skip transformation steps; introduce generated codes or identifiers; or need to explain deduplication, representative selection, inverse maps, matching, expansion, or reduction.
metadata:
  source: /home/lkroon/.agents/skills/worked-example-documentation
  migration-date: "2026-07-29"
---

# Worked-Example Documentation

## Objective

Make a non-obvious workflow auditable. A reader should be able to reproduce each displayed intermediate value from the preceding state and the stated rule.

## Workflow

1. Read the authoritative spec, implementation, fixtures, and executable evidence before drafting.
2. State the terminology and distinguish domain entities from implementation identifiers such as region codes, row indices, or representative IDs.
3. Build an evidence ledger mapping every displayed fact to its source file, command, or calculation.
4. Choose the smallest fixture that demonstrates contrasting behavior. Prefer records where one pair merges during deduplication, another remains distinct, and one fails or takes an edge path.
5. Keep the same records throughout the explanation. Do not swap examples between stages without saying so.
6. Show each transformation as input, rule, output, and why the output matters.
7. Verify displayed outcomes against executable code or authoritative data when available.

## Required Intermediate States

Include the applicable states rather than jumping from source to final output:

- source inputs and filters;
- ordered boundaries, vocabulary, schema, or lookup data;
- enumeration or identifier derivation;
- transformed records;
- projected dimensions or selected fields;
- unique representatives and inverse mappings;
- matching or evaluation outcomes;
- expansion to original order;
- final reduction or aggregation.

## Generated Identifiers

Explain how each identifier is calculated, not merely what it equals. Show the formula or enumeration rule, physical or logical ordering, exact-boundary behavior, values before and beyond the known range, missing values, and reserved sentinels. Explicitly say what the identifier does not represent.

## Evidence Rules

- Use verified fixture values; never invent convenient rows when repository data exists.
- Label partial tables with ellipses or “representative values”; do not imply completeness.
- Distinguish current behavior, proposed behavior, and measured evidence.
- Qualify local timings and environment-dependent measurements.
- If sources conflict, stop and report the conflict instead of silently choosing one.

## Presentation

Match the user's requested format. Prefer compact tables for state, formulas for derivations, and short prose for interpretation. Use one stable name per concept and repeat column order across stages.

## Completion Check

Confirm that every output can be derived from the shown rule, every displayed fact has a source, omitted data is marked, edge behavior is explained, and the final result matches authoritative evidence.
