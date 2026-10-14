# Measuring the impact of AI-assisted development

Adopting AI tools should make delivery **faster without making it worse**. We measure both
sides, at **team** level, before and after adoption. We never use these numbers to rank
individuals: that would only teach people to game them.

## 1. What we measure

The four DORA metrics plus flow and quality signals. Each one has a source we already have.

| Metric | Definition | Source | Watch for |
|---|---|---|---|
| **Lead time for changes** | First commit on a branch → deployed to production | Git + deploy pipeline timestamps | Faster coding but PRs waiting longer for review |
| **Deployment frequency** | Production deploys per week | Deploy pipeline | — |
| **Change failure rate** | % of deploys that cause a rollback, hotfix or incident | Deploys linked to incidents/reverts | The key "are we breaking more?" signal |
| **Time to restore** | Incident start → resolved | Incident tracker | — |
| **PR review time** | PR opened → approved; and number of review rounds | GitHub API | AI-assisted PRs being larger or harder to review |
| **PR size** | Changed lines per PR (median, p90) | GitHub API | AI making it too easy to produce big diffs |
| **Escaped defects** | Bugs found in production per 100 changes, by severity | Issue tracker (`bug` + `escaped` labels) | Quality regression that CI did not catch |
| **Defects caught by gates** | CI failures per PR by gate (tests, contract, scan, boundaries) | CI results | A healthy signal: the gates are doing their job |
| **Security findings** | New HIGH/CRITICAL findings per month (scanners, pentest) | Trivy, pip-audit, npm audit, pentest | — |
| **Developer experience** | Quarterly 5-question survey (flow, confidence, toil, learning, trust in AI output) | Survey | Juniors relying on AI without learning |

## 2. How we compare before and after

1. **Baseline:** collect 8–12 weeks of the metrics *before* rollout. Without a baseline every
   claim is anecdote.
2. **Rollout in cohorts** (e.g. two squads first), so we can compare against teams still
   working the old way over the same period. This removes seasonality and release-cycle noise.
3. **Segment by the `ai-assisted` PR label** to compare AI-assisted and other changes *within*
   the same team: review time, size, change failure rate and escaped defects.
4. **Look at distributions, not averages:** report median and p90, because averages hide the
   painful tail.
5. **Review monthly** in the engineering retro: what changed, what we will adjust (prompts,
   `AGENTS.md` rules, training, gates).

## 3. What "good" looks like

- Lead time **down**, deployment frequency **up**.
- Change failure rate and escaped defects **flat or down**. If they go up, speed gains do not
  count.
- PR size and review time **flat**. If AI makes PRs bigger, we coach smaller PRs rather than
  accept slower reviews.
- Gates catch issues *before* review, and the share of findings caught by automation grows.
- Survey: developers, especially juniors, report they are learning, not just shipping.

## 4. Guardrails on the measurement itself

- Team-level reporting only; no individual leaderboards.
- Metrics are inputs to a conversation, not targets (Goodhart's law).
- The label is about the *change*, not the *person*. Not labelling is a process issue, never
  a disciplinary one.

## 5. Example from this repository

Gate catches while building CareSlot with an AI agent: a formatting slip (CI lint → added
pre-commit hooks), a lax consent boolean and missing `Allow` header (contract tests), 41
fixable CVEs in a base image (container scan), and a duplicate connection pool hiding SQL
from traces (verified in Jaeger). Each became a regression test or a new guardrail. That loop
(**gate → fix → new guardrail**) is what we want the metrics to show at team scale.
