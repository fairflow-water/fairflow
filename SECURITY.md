<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Security policy

Fairflow is used in classrooms and will hold pseudonymous participant data (blueprint §10.4). Please report
vulnerabilities privately, never in a public issue, pull request or discussion.

## How to report

- Use GitHub's **private vulnerability reporting** on this repository ("Security" tab → "Report a vulnerability")
  once the repository is public.
- Until then, e-mail the maintainer listed in `CITATION.cff`, with "Fairflow security" in the subject.

Include what is affected (engine, mirror, record, room server, client), how to reproduce it, and the impact you see.
You will get an acknowledgement within five working days. A fix and a coordinated disclosure date are agreed with you.

## What counts

Of particular concern:

- any way for a participant to learn another participant's sealed actions (pumping) before the debrief, beyond what the
  in-play display intends (ADR 0004 and its leakage audit);
- any way to alter a Season Record without `audit()` detecting it;
- disclosure of participant data or linking codes;
- supply-chain issues in the build or release.

## Supported versions

Until v1.0, only the `main` branch is supported.
