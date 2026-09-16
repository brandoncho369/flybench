# Regenerate every derived number from the committed results (ROADMAP item 39). PowerShell 5.
#   .\reproduce.ps1          # lint, tests, LEADERBOARD.md and the explorer snapshot from results\
#   .\reproduce.ps1 -Full    # also rerun the two headline result files on the pinned connectomes (~40 min with -Jobs 6)
param([switch]$Full, [int]$Jobs = 6)
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = 1
python -m flybench lint
if (-not $?) { throw "lint failed" }
python -m pytest -q
if (-not $?) { throw "tests failed" }
if ($Full) {
  python -m flybench run -c flywire783 --gain 0.45 --seeds 3 --controls rewired --jobs $Jobs --label "LIF gain 0.45 (3 seeds)" -o results\flywire783_gain0.45.json
  if (-not $?) { throw "flywire run failed" }
  python -m flybench run -c malecns --gain 0.65 --seeds 3 --controls rewired --jobs $Jobs --label "MaleCNS gain 0.65 (Minecraft demo)" -o results\malecns-gain-0.65.json
  if (-not $?) { throw "malecns run failed" }
}
python -m flybench compare results -o LEADERBOARD.md
if (Test-Path ..\fly-explorer\scripts\leaderboard-snapshot.py) {
  Push-Location ..\fly-explorer
  python scripts\leaderboard-snapshot.py ..\flybench
  npm test
  Pop-Location
}
git status --short LEADERBOARD.md results ..\fly-explorer\src\data\leaderboard.json
Write-Host "reproduce: done. A non-empty status above means a committed number changed."
