# Reset the demo to a clean, unscored state before recording a walkthrough.
#
# Clears every lead, re-imports the sample dataset, and then stops. Enrichment
# is deliberately NOT run, so you can click "Score 13 leads" on camera and show
# the progress bar filling in.
#
# Override the defaults if you are serving the built app from the container:
#   $env:API="http://localhost:8080"; $env:APP="http://localhost:8080"; ./scripts/reset_demo.ps1
$ErrorActionPreference = "Stop"

$Api = if ($env:API) { $env:API } else { "http://localhost:8000" }
$App = if ($env:APP) { $env:APP } else { "http://localhost:5173" }

try {
    Invoke-RestMethod -Uri "$Api/api/health" -TimeoutSec 5 | Out-Null
} catch {
    Write-Host "The API is not responding at $Api"
    Write-Host ""
    Write-Host "Start it first:"
    Write-Host '  cd backend; $env:DEMO_MODE="true"; uvicorn app.main:app --reload --port 8000'
    exit 1
}

Write-Host "Clearing leads..."
Invoke-RestMethod -Method Delete -Uri "$Api/api/leads" | Out-Null

Write-Host "Importing the sample dataset..."
$report = Invoke-RestMethod -Method Post -Uri "$Api/api/leads/import-sample"

Write-Host "  $($report.added) leads imported, not yet scored."
Write-Host ""
Write-Host "Ready. Open: $App"
Write-Host "Then click `"Score $($report.added) leads`" to run enrichment on camera."
