---
name: unbounded-walk-skill
description: Fixture Skill that mentions large, real absolute directories in backticks (`/mnt/d`, `/`, `/home`), used to regression-test that the fact reporter never recurses into an out-of-scope directory candidate (F1/RD-01). Not a real tool.
---

# unbounded-walk-skill

This body documents a fixed output path under `/mnt/d` in prose, exactly
as a real team skill (render-deck) does. It also mentions the root `/`
and `/home` directly. None of these are support files this Skill bundles
— the reporter must record each as an out-of-scope directory candidate
and return quickly, never recurse into any of them.
