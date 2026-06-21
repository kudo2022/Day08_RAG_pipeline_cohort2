# Procurement law guide for this repo

**Official title:** Procurement-law quick guide for the seeded RAG corpus
**Official ID:** GUIDE/PROCUREMENT/2026
**Issued date:** 2026-06-21
**Effective date:** 2026-06-21
**Official URL:** https://vanban.chinhphu.vn/
**Domain:** procurement

---

## Corpus scope

This repository has been repurposed from a narcotics-law coursework project into a procurement-law agent.
The procurement-law agent is grounded in the following official Vietnam government sources:

1. `74/VBHN-VPQH` issued on `2026-03-25`, which is the consolidated Law on Procurement as of `2026-03-25`.
2. `24/2024/ND-CP` issued on `2024-02-27`, effective `2024-02-27`, guiding contractor selection.
3. `17/2025/ND-CP` issued on `2025-02-06`, effective `2025-02-06`, amending decrees implementing the Law on Procurement.
4. `23/2024/ND-CP` issued on `2024-02-27`, effective `2024-02-27`, guiding investor selection for sector-specific projects that must organize bidding.
5. `115/2024/ND-CP` issued on `2024-09-16`, effective `2024-09-16`, guiding investor selection for land-use projects.

## How to read the legal stack

Use the consolidated law first when the question asks about scope, principles, prohibited acts, responsibilities, transition rules, or the current wording of the Law on Procurement after amendments.

Use `24/2024/ND-CP` when the question asks how to organize contractor selection in practice, for example methods, procedures, online bidding, direct procurement, or implementation details below the law level.

Use `23/2024/ND-CP` and `115/2024/ND-CP` when the question is really about investor selection rather than contractor selection.
The former is oriented to sector-law projects that must be tendered, while the latter is oriented to projects that use land.

Use `17/2025/ND-CP` together with the other decrees whenever the question asks whether a rule changed during `2025`.

## Date-awareness notes

The base law `22/2023/QH15` took effect on `2024-01-01`.
It was amended by `57/2024/QH15`, effective `2025-01-15`, and by `90/2025/QH15`, effective `2025-07-01`.
The consolidated text `74/VBHN-VPQH` was issued later on `2026-03-25`, so it is the easiest anchor for the agent when a user asks "the current law" as of `2026-06-21`.

## Expected answer style

When the agent answers, it should cite the exact source it relied on.
If the retrieved context does not clearly confirm a threshold, an article number, or a transition rule, the answer should say that the point cannot be confirmed from the current corpus instead of guessing.
