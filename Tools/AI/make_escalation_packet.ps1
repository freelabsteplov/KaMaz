param(
    [string]$ProjectRoot,
    [string]$Goal = "TODO: Define the exact goal.",
    [string]$Hypothesis = "TODO: Define the current best hypothesis.",
    [string]$FilesToTouch = "",
    [string]$OpenQuestions = "TODO: Add open questions.",
    [int]$LogTail = 80
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

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

function Split-List {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return @()
    }

    return $Value -split '[,;\r\n]+' |
        ForEach-Object { $_.Trim() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
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

function Get-TextTail {
    param(
        [System.IO.FileInfo]$File,
        [int]$TailLines
    )

    if (-not $File) {
        return "No file available."
    }

    try {
        $content = Get-Content -LiteralPath $File.FullName -Tail $TailLines -ErrorAction Stop
        return ($content -join "`n")
    }
    catch {
        return "Failed to read $($File.FullName): $($_.Exception.Message)"
    }
}

$resolvedRoot = Resolve-ProjectRoot -ExplicitRoot $ProjectRoot
$escalationDir = Join-Path $resolvedRoot ".ai\escalations"
$aiLogsDir = Join-Path $resolvedRoot ".ai\logs"
New-Item -ItemType Directory -Path $escalationDir -Force | Out-Null
New-Item -ItemType Directory -Path $aiLogsDir -Force | Out-Null

$hasGit = $null -ne (Get-Command git -ErrorAction SilentlyContinue)

$branch = "N/A"
$statusShort = "git not available"
$diffStat = "git not available"
$changedTracked = @()
$untracked = @()

if ($hasGit) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $branchOut = @(& git -C $resolvedRoot rev-parse --abbrev-ref HEAD 2>$null)
        if ($LASTEXITCODE -eq 0 -and $branchOut) {
            $branch = ($branchOut | Select-Object -First 1)
        }

        $statusOut = @(& git -C $resolvedRoot status --short 2>$null)
        if ($statusOut) {
            $statusShort = ($statusOut -join "`n")
        }
        else {
            $statusShort = "working tree clean"
        }

        $diffStatOut = @(& git -C $resolvedRoot diff --stat 2>$null)
        if ($diffStatOut) {
            $diffStat = ($diffStatOut -join "`n")
        }
        else {
            $diffStat = "no tracked diff"
        }

        $changedTracked = @(& git -C $resolvedRoot diff --name-only --diff-filter=ACMRTUXB 2>$null)
        $untracked = @(& git -C $resolvedRoot ls-files --others --exclude-standard 2>$null)
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

$manualFiles = @(Split-List -Value $FilesToTouch)
$candidateFiles = @(@($manualFiles + $changedTracked + $untracked) |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
    Select-Object -Unique)

if (@($candidateFiles).Count -gt 30) {
    $candidateFiles = $candidateFiles | Select-Object -First 30
}

$openQuestions = @(Split-List -Value $OpenQuestions)
if (@($openQuestions).Count -eq 0) {
    $openQuestions = @("TODO: Add open questions.")
}

$latestBuildLog = Get-LatestFile -Directories @($aiLogsDir) -Patterns @("build_editor_*.log", "*.log")
$latestEditorLog = Get-LatestFile -Directories @((Join-Path $resolvedRoot "Saved\Logs")) -Patterns @("*.log")
$latestAutomationLog = Get-LatestFile -Directories @((Join-Path $resolvedRoot "Saved\BlueprintAutomation")) -Patterns @("*.txt", "*.log", "*.json")

$buildTail = Get-TextTail -File $latestBuildLog -TailLines $LogTail
$editorTail = Get-TextTail -File $latestEditorLog -TailLines $LogTail
$automationTail = Get-TextTail -File $latestAutomationLog -TailLines $LogTail
$latestBuildLogPath = if ($latestBuildLog) { $latestBuildLog.FullName } else { "N/A" }
$latestEditorLogPath = if ($latestEditorLog) { $latestEditorLog.FullName } else { "N/A" }
$latestAutomationLogPath = if ($latestAutomationLog) { $latestAutomationLog.FullName } else { "N/A" }

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$slug = ($Goal.ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
if ([string]::IsNullOrWhiteSpace($slug)) {
    $slug = "escalation"
}
if ($slug.Length -gt 48) {
    $slug = $slug.Substring(0, 48).Trim('-')
}

$packetPath = Join-Path $escalationDir "$timestamp-$slug.md"

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("# Senior Escalation Packet")
[void]$sb.AppendLine()
[void]$sb.AppendLine("- Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz")")
[void]$sb.AppendLine("- Project root: $resolvedRoot")
[void]$sb.AppendLine("- Branch: $branch")
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Goal")
[void]$sb.AppendLine()
[void]$sb.AppendLine($Goal)
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Hypothesis")
[void]$sb.AppendLine()
[void]$sb.AppendLine($Hypothesis)
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Files to touch")
[void]$sb.AppendLine()

if (@($candidateFiles).Count -gt 0) {
    foreach ($file in $candidateFiles) {
        [void]$sb.AppendLine("- $file")
    }
}
else {
    [void]$sb.AppendLine("- TODO: list concrete files before implementation")
}

[void]$sb.AppendLine()
[void]$sb.AppendLine("## Ordered steps")
[void]$sb.AppendLine()
[void]$sb.AppendLine("1. Reproduce the issue and confirm current behavior.")
[void]$sb.AppendLine("2. Inspect only the listed files and map the minimum safe change.")
[void]$sb.AppendLine("3. Apply the smallest patch that validates the hypothesis.")
[void]$sb.AppendLine("4. Validate with project wrappers (build_editor.ps1, read_last_logs.ps1, optional run_smoke.ps1).")
[void]$sb.AppendLine("5. If validation fails, revise hypothesis and iterate once with a narrow delta.")
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Invariants / Do-not-break rules")
[void]$sb.AppendLine()
[void]$sb.AppendLine("- Keep local-first routing as default.")
[void]$sb.AppendLine("- Do not break existing Unreal build loop or project wrapper workflow.")
[void]$sb.AppendLine("- Do not treat Live Coding as complete validation for reflection/header/module changes.")
[void]$sb.AppendLine("- Keep edits small, reviewable, and scoped to the task.")
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Validation")
[void]$sb.AppendLine()
[void]$sb.AppendLine("- Run Tools/AI/build_editor.ps1 for compile-pass.")
[void]$sb.AppendLine("- Run Tools/AI/read_last_logs.ps1 to inspect editor/build output.")
[void]$sb.AppendLine("- Run Tools/AI/run_smoke.ps1 (and -RunHeadless when needed).")
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Rollback notes")
[void]$sb.AppendLine()
[void]$sb.AppendLine("- Revert only files listed in this packet if regression appears.")
[void]$sb.AppendLine("- Prefer rolling back the smallest failing patch, not the whole branch.")
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Current diff summary")
[void]$sb.AppendLine()
[void]$sb.AppendLine("### git status --short")
[void]$sb.AppendLine()
[void]$sb.AppendLine("~~~text")
[void]$sb.AppendLine($statusShort)
[void]$sb.AppendLine("~~~")
[void]$sb.AppendLine()
[void]$sb.AppendLine("### git diff --stat")
[void]$sb.AppendLine()
[void]$sb.AppendLine("~~~text")
[void]$sb.AppendLine($diffStat)
[void]$sb.AppendLine("~~~")
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Recent build/log excerpts")
[void]$sb.AppendLine()
[void]$sb.AppendLine("### Latest AI build log")
[void]$sb.AppendLine("- File: $latestBuildLogPath")
[void]$sb.AppendLine("~~~text")
[void]$sb.AppendLine($buildTail)
[void]$sb.AppendLine("~~~")
[void]$sb.AppendLine()
[void]$sb.AppendLine("### Latest Unreal editor log")
[void]$sb.AppendLine("- File: $latestEditorLogPath")
[void]$sb.AppendLine("~~~text")
[void]$sb.AppendLine($editorTail)
[void]$sb.AppendLine("~~~")
[void]$sb.AppendLine()
[void]$sb.AppendLine("### Latest Blueprint automation log")
[void]$sb.AppendLine("- File: $latestAutomationLogPath")
[void]$sb.AppendLine("~~~text")
[void]$sb.AppendLine($automationTail)
[void]$sb.AppendLine("~~~")
[void]$sb.AppendLine()
[void]$sb.AppendLine("## Open questions")
[void]$sb.AppendLine()
foreach ($q in $openQuestions) {
    [void]$sb.AppendLine("- $q")
}

Set-Content -LiteralPath $packetPath -Value $sb.ToString() -Encoding UTF8

Write-Host "Escalation packet written:"
Write-Host $packetPath
