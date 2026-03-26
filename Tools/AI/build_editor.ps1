param(
    [string]$ProjectRoot,
    [string]$UProjectPath,
    [string]$Target,
    [string]$BuildBatPath,
    [ValidateSet("Development", "DebugGame", "Debug")]
    [string]$Configuration = "Development",
    [string]$Platform = "Win64",
    [switch]$Clean,
    [switch]$DryRun
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

function Resolve-UProjectPath {
    param(
        [string]$Root,
        [string]$ExplicitUProject
    )

    if ($ExplicitUProject) {
        if (-not (Test-Path -LiteralPath $ExplicitUProject)) {
            throw "UProject path does not exist: $ExplicitUProject"
        }
        return (Resolve-Path -LiteralPath $ExplicitUProject).Path
    }

    $topLevel = @(Get-ChildItem -Path $Root -Filter "*.uproject" -File -ErrorAction SilentlyContinue)
    if ($topLevel.Count -eq 1) {
        return $topLevel[0].FullName
    }

    if ($topLevel.Count -gt 1) {
        $names = $topLevel | ForEach-Object { $_.Name } | Sort-Object
        throw "Multiple top-level .uproject files found. Specify -UProjectPath explicitly. Found: $($names -join ', ')"
    }

    $recursive = @(Get-ChildItem -Path $Root -Filter "*.uproject" -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '[\\/]\_PluginBuild[\\/]' })

    if ($recursive.Count -eq 1) {
        return $recursive[0].FullName
    }

    if ($recursive.Count -gt 1) {
        $names = $recursive | ForEach-Object { $_.FullName } | Sort-Object
        throw "Multiple candidate .uproject files found. Specify -UProjectPath explicitly. Found: $($names -join '; ')"
    }

    throw "No .uproject file found under $Root"
}

function Resolve-EditorTarget {
    param(
        [string]$Root,
        [string]$UProject,
        [string]$ExplicitTarget
    )

    if ($ExplicitTarget) {
        return $ExplicitTarget
    }

    $sourceDir = Join-Path $Root "Source"
    if (-not (Test-Path -LiteralPath $sourceDir)) {
        throw "Source directory not found: $sourceDir"
    }

    $editorTargets = @(Get-ChildItem -Path $sourceDir -Filter "*Editor.Target.cs" -File -ErrorAction SilentlyContinue)

    if ($editorTargets.Count -eq 1) {
        return ($editorTargets[0].Name -replace '\.Target\.cs$', '')
    }

    if ($editorTargets.Count -gt 1) {
        $names = $editorTargets | ForEach-Object { $_.Name -replace '\.Target\.cs$', '' } | Sort-Object
        throw "Multiple editor targets found. Specify -Target explicitly. Found: $($names -join ', ')"
    }

    try {
        $uprojectJson = Get-Content -Raw -LiteralPath $UProject | ConvertFrom-Json
        $modules = @($uprojectJson.Modules)
        if ($modules.Count -gt 0 -and $modules[0].Name) {
            $candidate = "$($modules[0].Name)Editor"
            $candidatePath = Join-Path $sourceDir "$candidate.Target.cs"
            if (Test-Path -LiteralPath $candidatePath) {
                return $candidate
            }
        }
    }
    catch {
        Write-Warning "Could not parse $UProject for module fallback: $($_.Exception.Message)"
    }

    throw "Editor target could not be determined automatically. Specify -Target explicitly."
}

function Resolve-BuildBatPath {
    param(
        [string]$UProject,
        [string]$ExplicitBuildBat
    )

    if ($ExplicitBuildBat) {
        if (-not (Test-Path -LiteralPath $ExplicitBuildBat)) {
            throw "Build.bat path does not exist: $ExplicitBuildBat"
        }
        return (Resolve-Path -LiteralPath $ExplicitBuildBat).Path
    }

    $engineAssociation = $null
    try {
        $uprojectJson = Get-Content -Raw -LiteralPath $UProject | ConvertFrom-Json
        $engineAssociation = [string]$uprojectJson.EngineAssociation
    }
    catch {
        Write-Warning ("Could not read EngineAssociation from {0}: {1}" -f $UProject, $_.Exception.Message)
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    $epicBase = Join-Path $env:ProgramFiles "Epic Games"

    if (-not [string]::IsNullOrWhiteSpace($engineAssociation)) {
        $normalized = if ($engineAssociation.StartsWith("UE_")) { $engineAssociation } else { "UE_$engineAssociation" }
        $candidates.Add((Join-Path $epicBase "$normalized\Engine\Build\BatchFiles\Build.bat"))
        $candidates.Add((Join-Path $epicBase "$normalized\$normalized\Engine\Build\BatchFiles\Build.bat"))
    }

    if (Test-Path -LiteralPath $epicBase) {
        $engineFolders = Get-ChildItem -Path $epicBase -Directory -Filter "UE_*" -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($folder in $engineFolders) {
            $leaf = Split-Path -Path $folder.FullName -Leaf
            $candidates.Add((Join-Path $folder.FullName "Engine\Build\BatchFiles\Build.bat"))
            $candidates.Add((Join-Path $folder.FullName "$leaf\Engine\Build\BatchFiles\Build.bat"))
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Could not find Unreal Build.bat automatically. Pass -BuildBatPath explicitly."
}

$resolvedRoot = Resolve-ProjectRoot -ExplicitRoot $ProjectRoot
$resolvedUProject = Resolve-UProjectPath -Root $resolvedRoot -ExplicitUProject $UProjectPath
$resolvedTarget = Resolve-EditorTarget -Root $resolvedRoot -UProject $resolvedUProject -ExplicitTarget $Target
$resolvedBuildBat = Resolve-BuildBatPath -UProject $resolvedUProject -ExplicitBuildBat $BuildBatPath

$aiLogsDir = Join-Path $resolvedRoot ".ai\logs"
New-Item -ItemType Directory -Path $aiLogsDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $aiLogsDir "build_editor_$timestamp.log"

$buildArgs = @(
    $resolvedTarget
    $Platform
    $Configuration
    "-Project=$resolvedUProject"
    "-WaitMutex"
    "-NoHotReloadFromIDE"
)

if ($Clean) {
    $buildArgs += "-Clean"
}

Write-Host "Project root : $resolvedRoot"
Write-Host "UProject     : $resolvedUProject"
Write-Host "Target       : $resolvedTarget"
Write-Host "Build.bat    : $resolvedBuildBat"
Write-Host "Configuration: $Configuration"
Write-Host "Platform     : $Platform"
Write-Host "Log file     : $logFile"
Write-Host ""

if ($DryRun) {
    Write-Host "DryRun enabled. Command preview:"
    Write-Host "& `"$resolvedBuildBat`" $($buildArgs -join ' ')"
    exit 0
}

& $resolvedBuildBat @buildArgs *>&1 | Tee-Object -FilePath $logFile
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "Editor build failed with exit code $exitCode. See $logFile"
}

Write-Host ""
Write-Host "Editor build succeeded."
Write-Host "Build log saved to: $logFile"
