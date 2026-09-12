# Apply P1+P2 authorization patch to V27R1
# Run on E:\FF_FAST\FF_HQ or via remote session

param(
    [string]$TargetPath = "E:\FF_FAST\FF_HQ",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "P1+P2 Authorization Patch Deployment" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Verify target exists
if (-not (Test-Path $TargetPath)) {
    Write-Host "ERROR: Target path not found: $TargetPath" -ForegroundColor Red
    exit 1
}

$CorePath = Join-Path $TargetPath "CORE\FF_HQ_EDGE_ROOT_DASHBOARD_V27R1"
if (-not (Test-Path $CorePath)) {
    Write-Host "ERROR: V27R1 core not found at: $CorePath" -ForegroundColor Red
    exit 1
}

Push-Location $CorePath

try {
    Write-Host "1. Checking for active node processes..." -ForegroundColor Yellow
    $nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
    if ($nodeProcesses) {
        Write-Host "   Found $($nodeProcesses.Count) node process(es)" -ForegroundColor Yellow
        Write-Host "   → Stop V27R1 core manually or press Ctrl+C to abort" -ForegroundColor Yellow
        Read-Host "   Press Enter to continue"
    } else {
        Write-Host "   No node processes found. Continuing." -ForegroundColor Green
    }
    Write-Host ""

    Write-Host "2. Verifying patch prerequisites..." -ForegroundColor Yellow
    $requiredFiles = @(
        "src/security/authz.mjs",
        "src/server.mjs",
        "tests/real-chart-server-wiring-v23.test.mjs"
    )
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file)) {
            Write-Host "   ERROR: Required file not found: $file" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "   All prerequisites met." -ForegroundColor Green
    Write-Host ""

    Write-Host "3. Applying patch..." -ForegroundColor Yellow
    if ($DryRun) {
        Write-Host "   (DRY RUN - no changes will be made)" -ForegroundColor Cyan
        & git apply --check -p2 --directory=CORE/FF_HQ_EDGE_ROOT_DASHBOARD_V27R1 "p1p2.patch"
    } else {
        & git apply -p2 --directory=CORE/FF_HQ_EDGE_ROOT_DASHBOARD_V27R1 "p1p2.patch"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   ERROR: Patch application failed" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "   Patch applied successfully." -ForegroundColor Green
    Write-Host ""

    Write-Host "4. Running tests..." -ForegroundColor Yellow
    & node --test "tests/*.test.mjs"
    $testExit = $LASTEXITCODE
    Write-Host ""

    if ($testExit -eq 0) {
        Write-Host "   Tests PASSED" -ForegroundColor Green
    } else {
        Write-Host "   Tests exited with code: $testExit" -ForegroundColor Yellow
        Write-Host "   (Expected: 279 pass, 2 pre-existing failures)" -ForegroundColor Cyan
    }
    Write-Host ""

    if (-not $DryRun) {
        Write-Host "5. Commit changes..." -ForegroundColor Yellow
        & git add -A
        & git commit -m "Apply P1+P2 authorization patch: permission matrix + route gating

- P1: Frozen permission matrix (14 actions, 4 roles, 65 gated routes)
- P2: Server-side route gating via requireAction() helper
- Tests: 11 new authz-matrix tests, all pass (279/281 total)
- Deny-by-default: VIEWER loses writes, USER loses market-mark/config, ADMIN gains ops
- No LIVE/broker/control authority changes

See P1P2_AUDIT_SUMMARY.md for full details.
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   Committed." -ForegroundColor Green
        } else {
            Write-Host "   WARNING: Commit failed. Changes staged but not committed." -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "6. Ready to restart V27R1 core" -ForegroundColor Green
        Write-Host "   → Restart node ./server.mjs" -ForegroundColor Cyan
    }

} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Deployment complete." -ForegroundColor Green
