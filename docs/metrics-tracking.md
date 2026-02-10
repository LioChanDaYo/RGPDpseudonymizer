# Success Metrics Tracking

**Internal document** — Tracks key metrics for the GDPR Pseudonymizer project post-launch.

## Metrics to Track

| Metric | Source | How to Check |
|--------|--------|--------------|
| **PyPI Downloads** | PyPI / pypistats | `pip install pypistats && pypistats recent gdpr-pseudonymizer` |
| **GitHub Stars** | GitHub repo page | [Repository page](https://github.com/LioChanDaYo/RGPDpseudonymizer) |
| **GitHub Forks** | GitHub repo page | Same as above |
| **Open Issues** | GitHub Issues | `gh issue list --state open` |
| **Closed Issues** | GitHub Issues | `gh issue list --state closed` |
| **Discussions Activity** | GitHub Discussions | [Discussions page](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions) |
| **Documentation Views** | GitHub Pages Analytics | GitHub repo → Insights → Traffic |

## Manual Check Commands

```bash
# PyPI download stats (install pypistats first)
pip install pypistats
pypistats recent gdpr-pseudonymizer
pypistats overall gdpr-pseudonymizer

# GitHub stats via CLI
gh api repos/LioChanDaYo/RGPDpseudonymizer --jq '{stars: .stargazers_count, forks: .forks_count, watchers: .subscribers_count, open_issues: .open_issues_count}'

# Issue volume
gh issue list --state all --limit 100 | wc -l
```

## Tracking Schedule

| Frequency | Action |
|-----------|--------|
| Weekly (first month) | Check PyPI downloads, GitHub stars, new issues |
| Monthly (after first month) | Full metrics review, update this document |
| Quarterly | Trend analysis, roadmap adjustment |

## Baseline (Launch Day — 2026-02-11)

| Metric | Value |
|--------|-------|
| PyPI Downloads | 0 (not yet published) |
| GitHub Stars | TBD (after repo goes public) |
| Open Issues | TBD |
| Tests | 1077+ |
| Coverage | 86%+ |
