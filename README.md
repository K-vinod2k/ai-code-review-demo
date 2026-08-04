# AI Code Review Demo

A small TypeScript service used to demonstrate automated pull request review.

Every pull request is reviewed automatically by an AI reviewer that comments on
the diff. It never blocks a merge: measured recall on a labelled set ranged
26.7% to 80% across identical runs, so it advises and a human decides.

See `.github/workflows/review.yml`.
