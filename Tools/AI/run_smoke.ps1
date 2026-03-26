param(
    [string]$ProjectRoot,
    [string]$UProjectPath,
    [switch]$RunHeadless,
    [string]$Map = "/Game/Maps/MoscowEA5",
    [string]$SmokeCommand = "BlueprintAutomation.RunSmokeTest",
    [string]$PythonScriptPath
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

    throw "No top-level .uproject found in $Root"
}

function Resolve-UnrealEditorCmd {
    param([string]$UProject)

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
        $candidates.Add((Join-Path $epicBase "$normalized\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"))
        $candidates.Add((Join-Path $epicBase "$normalized\$normalized\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"))
    }

    if (Test-Path -LiteralPath $epicBase) {
        $engineFolders = Get-ChildItem -Path $epicBase -Directory -Filter "UE_*" -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($folder in $engineFolders) {
            $leaf = Split-Path -Path $folder.FullName -Leaf
            $candidates.Add((Join-Path $folder.FullName "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"))
            $candidates.Add((Join-Path $folder.FullName "$leaf\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"))
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Could not auto-detect UnrealEditor-Cmd.exe. Install path may differ from expected Epic Games layout."
}

$resolvedRoot = Resolve-ProjectRoot -ExplicitRoot $ProjectRoot
$resolvedUProject = Resolve-UProjectPath -Root $resolvedRoot -ExplicitUProject $UProjectPath

$requiredWrappers = @(
    "Tools/AI/build_editor.ps1",
    "Tools/AI/read_last_logs.ps1",
    "Tools/AI/make_escalation_packet.ps1"
)

foreach ($relativePath in $requiredWrappers) {
    $absolutePath = Join-Path $resolvedRoot $relativePath
    if (-not (Test-Path -LiteralPath $absolutePath)) {
        throw "Required wrapper missing: $relativePath"
    }
}

Write-Host "Project root : $resolvedRoot"
Write-Host "UProject     : $resolvedUProject"
Write-Host "Smoke mode   : $(if ($RunHeadless) { 'headless' } else { 'safe-local' })"
Write-Host ""

if (-not $RunHeadless) {
    Write-Host "Safe-local smoke passed."
    Write-Host "Run with -RunHeadless to execute UnrealEditor-Cmd smoke command."
    exit 0
}

$editorCmd = Resolve-UnrealEditorCmd -UProject $resolvedUProject
$aiLogsDir = Join-Path $resolvedRoot ".ai\logs"
New-Item -ItemType Directory -Path $aiLogsDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $aiLogsDir "run_smoke_$timestamp.log"
$engineLogFile = Join-Path $aiLogsDir "run_smoke_engine_$timestamp.log"
$stdoutFile = Join-Path $aiLogsDir "run_smoke_stdout_$timestamp.log"
$stderrFile = Join-Path $aiLogsDir "run_smoke_stderr_$timestamp.log"

if ($PythonScriptPath) {
    if (-not (Test-Path -LiteralPath $PythonScriptPath)) {
        throw "Python script path does not exist: $PythonScriptPath"
    }
    $resolvedPythonScript = ((Resolve-Path -LiteralPath $PythonScriptPath).Path -replace '\\', '/')
}

$args = @(
    ('"{0}"' -f $resolvedUProject)
    $Map
)

if ($PythonScriptPath) {
    $args += ('-ExecutePythonScript="{0}"' -f $resolvedPythonScript)
}
else {
    $args += ('-ExecCmds="{0};Quit"' -f $SmokeCommand)
}

$args += @(
    "-unattended"
    "-nop4"
    "-nosplash"
    "-stdout"
    "-FullStdOutLogOutput"
    "-UTF8Output"
    ('-AbsLog="{0}"' -f $engineLogFile)
)

Write-Host "UnrealEditor-Cmd: $editorCmd"
Write-Host "Map             : $Map"
if ($PythonScriptPath) {
    Write-Host "Python script   : $resolvedPythonScript"
}
else {
    Write-Host "Command         : $SmokeCommand"
}
Write-Host "Log file        : $logFile"
Write-Host "Engine log      : $engineLogFile"
Write-Host "Stdout log      : $stdoutFile"
Write-Host "Stderr log      : $stderrFile"
Write-Host ""

if (Test-Path -LiteralPath $logFile) {
    Remove-Item -LiteralPath $logFile -Force
}

$process = Start-Process `
    -FilePath $editorCmd `
    -ArgumentList $args `
    -NoNewWindow `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $stdoutFile `
    -RedirectStandardError $stderrFile

foreach ($captureFile in @($stdoutFile, $stderrFile)) {
    if (-not (Test-Path -LiteralPath $captureFile)) {
        continue
    }

    Get-Content -LiteralPath $captureFile | Tee-Object -FilePath $logFile -Append
}

$exitCode = $process.ExitCode

if ($exitCode -ne 0) {
    throw "Headless smoke run failed with exit code $exitCode. See $logFile and $engineLogFile"
}

$rawLog = Get-Content -Raw -LiteralPath $logFile -ErrorAction SilentlyContinue
if ($rawLog -match "Unknown command|not recognized") {
    Write-Warning "Smoke command may be unavailable in this project/engine build. Check $logFile"
}

Write-Host ""
Write-Host "Headless smoke completed. Log saved to: $logFile"
Write-Host "Engine log saved to      : $engineLogFile"
