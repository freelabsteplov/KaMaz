param(
    [string]$ProjectRoot,
    [int]$Tail = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ProjectRoot {
    param([string]$ExplicitRoot)

    if ($ExplicitRoot) {
        if (-not (Test-Path -LiteralPath $ExplicitRoot)) {
            throw "ProjectRoot does not exist: $ExplicitRoot"
        }
        return (Resolve-Path -LiteralPath $ExplicitRoot).Path
    }

    $start = Split-Path -Parent $PSCommandPath
    $current = (Resolve-Path -LiteralPath $start).Path

    while ($true) {
        $uprojects = @(Get-ChildItem -Path $current -Filter "*.uproject" -File -ErrorAction SilentlyContinue)
        if ($uprojects.Count -gt 0) {
            return $current
        }

        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
            throw "Could not auto-detect project root from script path."
        }

        $current = $parent
    }
}

function Get-LatestFile {
    param(
        [string[]]$Directories,
        [string[]]$Patterns
    )

    $found = New-Object System.Collections.Generic.List[System.IO.FileInfo]

    foreach ($dir in $Directories) {
        if (-not (Test-Path -LiteralPath $dir)) {
            continue
        }

        foreach ($pattern in $Patterns) {
            $items = Get-ChildItem -Path $dir -File -Filter $pattern -ErrorAction SilentlyContinue
            foreach ($item in $items) {
                $found.Add($item)
            }
        }
    }

    if ($found.Count -eq 0) {
        return $null
    }

    return $found | Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

function Show-LogTail {
    param(
        [string]$Title,
        [System.IO.FileInfo]$File,
        [int]$TailLines
    )

    if (-not $File) {
        Write-Host "===== $Title ====="
        Write-Host "Not found."
        Write-Host ""
        return $false
    }

    Write-Host "===== $Title ====="
    Write-Host "Path   : $($File.FullName)"
    Write-Host "Updated: $($File.LastWriteTime)"
    Write-Host ""
    Get-Content -LiteralPath $File.FullName -Tail $TailLines
    Write-Host ""
    return $true
}

$resolvedRoot = Resolve-ProjectRoot -ExplicitRoot $ProjectRoot

$aiLogsDir = Join-Path $resolvedRoot ".ai\logs"
$savedLogsDir = Join-Path $resolvedRoot "Saved\Logs"
$savedBlueprintAutomationA = Join-Path $resolvedRoot "Saved\BlueprintAutomation"
$savedBlueprintAutomationB = Join-Path $resolvedRoot "Saved\BlueprintAutomation"
$savedCrashesDir = Join-Path $resolvedRoot "Saved\Crashes"

$latestBuildLog = Get-LatestFile -Directories @($aiLogsDir) -Patterns @("build_editor_*.log", "*.log")
$latestEditorLog = Get-LatestFile -Directories @($savedLogsDir) -Patterns @("*.log")
$latestAutomationLog = Get-LatestFile -Directories @($savedBlueprintAutomationA, $savedBlueprintAutomationB) -Patterns @("*.txt", "*.log", "*.json")

$latestCrashLog = $null
if (Test-Path -LiteralPath $savedCrashesDir) {
    $latestCrashLog = Get-ChildItem -Path $savedCrashesDir -File -Recurse -Include *.log, *.txt -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

Write-Host "Project root: $resolvedRoot"
Write-Host "Tail lines  : $Tail"
Write-Host ""

$shownCount = 0
if (Show-LogTail -Title "Latest AI Build Log" -File $latestBuildLog -TailLines $Tail) { $shownCount++ }
if (Show-LogTail -Title "Latest Unreal Editor Log" -File $latestEditorLog -TailLines $Tail) { $shownCount++ }
if (Show-LogTail -Title "Latest Blueprint Automation Log" -File $latestAutomationLog -TailLines $Tail) { $shownCount++ }
if (Show-LogTail -Title "Latest Crash Log" -File $latestCrashLog -TailLines $Tail) { $shownCount++ }

if ($shownCount -eq 0) {
    Write-Warning "No logs were found in expected locations."
    Write-Host "Checked:"
    Write-Host "  $aiLogsDir"
    Write-Host "  $savedLogsDir"
    Write-Host "  $savedBlueprintAutomationA"
    Write-Host "  $savedBlueprintAutomationB"
    Write-Host "  $savedCrashesDir"
}
