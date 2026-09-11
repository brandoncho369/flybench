These files belong under `.github/`, which some tools refuse to write into. Move them:

    mkdir .github\workflows
    move ci\ci.yml .github\workflows\ci.yml
    move ci\leaderboard.yml .github\workflows\leaderboard.yml
    move ci\evaluate.yml .github\workflows\evaluate.yml
    move ci\PULL_REQUEST_TEMPLATE.md .github\PULL_REQUEST_TEMPLATE.md
    rmdir /s /q ci

Then in the repo settings: Branches → add a rule for the default branch requiring the `ci` check to pass and one approving review before merge. That plus GitHub's own abuse limits is the rate limiting: nothing reaches the leaderboard without CI green and a human click.

Then publish the prebuilt connectome cache that `evaluate` downloads (one-time, from the flybench folder):

    gh release create cache-flywire783 flywire783-cache.zip --title "FlyWire v783 prebuilt cache" --notes "Built by flybench build from Codex v783 (Connections (Filtered), July 2025). FlyWire data: CC BY 4.0, Dorkenwald et al. 2024 / Schlegel et al. 2024."
