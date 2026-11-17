[CmdletBinding()]
param(
    [string]$Token = "",
    [string]$SonarHostUrl = "http://sonar.srv001",
    [string]$ProjectKey = "HAD",
    [string]$ProjectPath = ""
)

$ErrorActionPreference = "Stop"

# Projektwurzel: zwei Ebenen ueber diesem Skript
if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = (Get-Item "$PSScriptRoot\..\..").FullName
}

Write-Host "=================================================="
Write-Host "HomeAssistant (HAD) SonarQube Scan & Summary"
Write-Host "=================================================="
Write-Host ""

if (-not (Test-Path -Path $ProjectPath)) {
    throw "Projektpfad nicht gefunden: $ProjectPath"
}

Set-Location $ProjectPath

# SonarScanner in den PATH aufnehmen
if (Test-Path "C:\sonar-scanner\bin") {
    if ($env:Path -notlike "*C:\sonar-scanner\bin*") {
        $env:Path += ";C:\sonar-scanner\bin"
    }
}

# Token-Aufloesung mit klarer Prioritaet:
#   1. -Token Parameter (explizit)
#   2. .env im Projektwurzelverzeichnis (projektspezifisch)
#   3. Umgebungsvariable SONAR_TOKEN (globaler Fallback)
# Ein global gesetztes SONAR_TOKEN (z. B. aus einem anderen Projekt) darf den
# projektspezifischen Wert aus .env nicht ueberschreiben.
$TokenSource = ""
if (-not [string]::IsNullOrWhiteSpace($Token)) {
    $TokenSource = "Parameter -Token"
} else {
    $DotEnvPath = Join-Path $ProjectPath ".env"
    if (Test-Path -Path $DotEnvPath) {
        $EnvMatch = Get-Content $DotEnvPath | Select-String -Pattern '^\s*SONAR_TOKEN\s*=\s*(.+)$'
        if ($EnvMatch) {
            $Token = $EnvMatch.Matches.Groups[1].Value.Trim(" `"'")
            if (-not [string]::IsNullOrWhiteSpace($Token)) {
                $TokenSource = ".env"
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace($Token) -and -not [string]::IsNullOrWhiteSpace($env:SONAR_TOKEN)) {
        $Token = $env:SONAR_TOKEN
        $TokenSource = "Umgebungsvariable SONAR_TOKEN"
    }
}

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "Kein Sonar-Token gefunden. -Token setzen, .env mit SONAR_TOKEN=... anlegen oder SONAR_TOKEN exportieren."
}

# Ein global gesetztes SONAR_TOKEN wuerde sonst vom Scanner gegenueber
# -Dsonar.token nicht zuverlaessig ueberschrieben. Deshalb die aufgeloeste
# Variable explizit setzen.
if ($env:SONAR_TOKEN -and $env:SONAR_TOKEN -ne $Token) {
    Write-Warning "Globales SONAR_TOKEN weicht vom verwendeten Token ab und wird fuer diesen Lauf ueberschrieben."
}
$env:SONAR_TOKEN = $Token
Write-Host "[Auth] Sonar-Token geladen (Quelle: $TokenSource)." -ForegroundColor DarkGreen

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$OutputDir = Join-Path $PSScriptRoot "reports"
if (-not (Test-Path -Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$SummaryFile = Join-Path $OutputDir "${Timestamp}_sonar_summary.md"
$DetailsFile = Join-Path $OutputDir "${Timestamp}_sonar_details.md"

# 1. Tests mit Coverage
Write-Host "[1/4] Tests und Coverage erzeugen..." -ForegroundColor Cyan
python -m coverage run --source=signal-bridge -m pytest signal-bridge/tests -q
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Tests sind mit Fehlern beendet worden."
}
python -m coverage xml -o coverage.xml

# 2. Scan
Write-Host "[2/4] Sonar-Scan ausloesen..." -ForegroundColor Cyan

$sonarArgs = @(
    "-Dsonar.host.url=$SonarHostUrl",
    "-Dsonar.projectKey=$ProjectKey",
    "-Dsonar.projectName=$ProjectKey",
    "-Dsonar.sources=signal-bridge",
    "-Dsonar.tests=signal-bridge/tests",
    # Tests liegen unterhalb von sonar.sources. Ohne diesen Ausschluss
    # indexiert der Scanner dieselbe Datei zweimal (Haupt- und Testdatei).
    "-Dsonar.exclusions=signal-bridge/tests/**",
    "-Dsonar.python.coverage.reportPaths=coverage.xml",
    "-Dsonar.python.version=3.14",
    "-Dsonar.sourceEncoding=UTF-8"
)

# Token sowohl ueber die Umgebung als auch als Property uebergeben.
# Die Umgebungsvariable allein wird von der Scanner-CLI nicht zuverlaessig
# ausgewertet.
$env:SONAR_TOKEN = $Token
$sonarArgs += "-Dsonar.token=$Token"

if (Get-Command "sonar-scanner" -ErrorAction SilentlyContinue) {
    sonar-scanner @sonarArgs
} elseif (Test-Path "C:\sonar-scanner\bin\sonar-scanner.bat") {
    & "C:\sonar-scanner\bin\sonar-scanner.bat" @sonarArgs
} else {
    throw "sonar-scanner nicht gefunden."
}

if ($LASTEXITCODE -ne 0) {
    throw "Sonar-Scan ist fehlgeschlagen."
}

# 3. Auf Serververarbeitung warten
Write-Host ""
Write-Host "[3/4] Warte auf Serververarbeitung..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# 4. Ergebnisse ueber die REST-API holen
Write-Host "[4/4] Metriken und Findings abrufen..." -ForegroundColor Cyan

$Headers = @{}
$Bytes = [System.Text.Encoding]::ASCII.GetBytes("${Token}:")
$Headers.Authorization = "Basic " + [Convert]::ToBase64String($Bytes)

function Invoke-SonarApi {
    param([string]$Endpoint)
    try {
        return Invoke-RestMethod -Uri "$SonarHostUrl/api/$Endpoint" -Headers $Headers -Method Get
    }
    catch {
        Write-Warning "API-Abruf fehlgeschlagen fuer ${Endpoint}: $($_.Exception.Message)"
        return $null
    }
}

$QgData       = Invoke-SonarApi "qualitygates/project_status?projectKey=$ProjectKey"
$IssuesData   = Invoke-SonarApi "issues/search?componentKeys=$ProjectKey&statuses=OPEN,CONFIRMED,REOPENED&ps=500"
$SecIssues    = Invoke-SonarApi "issues/search?componentKeys=$ProjectKey&statuses=OPEN,CONFIRMED,REOPENED&impactSoftwareQualities=SECURITY&ps=500"
$RelIssues    = Invoke-SonarApi "issues/search?componentKeys=$ProjectKey&statuses=OPEN,CONFIRMED,REOPENED&impactSoftwareQualities=RELIABILITY&ps=500"
$MaintIssues  = Invoke-SonarApi "issues/search?componentKeys=$ProjectKey&statuses=OPEN,CONFIRMED,REOPENED&impactSoftwareQualities=MAINTAINABILITY&ps=500"
$CoverageData = Invoke-SonarApi "measures/component?component=$ProjectKey&metricKeys=coverage,lines_to_cover,uncovered_lines"
$DupData      = Invoke-SonarApi "measures/component?component=$ProjectKey&metricKeys=duplicated_lines_density,duplicated_lines,duplicated_blocks,duplicated_files"

$QgStatus    = if ($QgData -and $QgData.projectStatus) { $QgData.projectStatus.status } else { "UNKNOWN" }
$TotalIssues = if ($IssuesData -and $null -ne $IssuesData.total) { $IssuesData.total } else { 0 }
$SecCount    = if ($SecIssues -and $null -ne $SecIssues.total) { $SecIssues.total } else { 0 }
$RelCount    = if ($RelIssues -and $null -ne $RelIssues.total) { $RelIssues.total } else { 0 }
$MaintCount  = if ($MaintIssues -and $null -ne $MaintIssues.total) { $MaintIssues.total } else { 0 }

$SeverityGroups = @()
$RuleGroups = @()
if ($IssuesData -and $IssuesData.issues) {
    $SeverityGroups = $IssuesData.issues | Group-Object -Property severity -NoElement | Sort-Object Count -Descending
    $RuleGroups = $IssuesData.issues | Group-Object -Property rule -NoElement | Sort-Object Count -Descending | Select-Object -First 5
}

function Get-Measure {
    param($Data, [string]$Metric)
    if (-not $Data -or -not $Data.component -or -not $Data.component.measures) { return "-" }
    $Value = ($Data.component.measures | Where-Object { $_.metric -eq $Metric }).value
    if ($null -eq $Value) { return "-" }
    return $Value
}

$CoveragePct    = Get-Measure $CoverageData "coverage"
$LinesToCover   = Get-Measure $CoverageData "lines_to_cover"
$UncoveredLines = Get-Measure $CoverageData "uncovered_lines"
$DupDensity     = Get-Measure $DupData "duplicated_lines_density"
$DupLines       = Get-Measure $DupData "duplicated_lines"
$DupBlocks      = Get-Measure $DupData "duplicated_blocks"
$DupFiles       = Get-Measure $DupData "duplicated_files"

# 5. Summary
$SummaryMarkdown = @"
# SonarQube Analysis Summary

**Projekt:** $ProjectKey
**Zeitpunkt:** $Timestamp
**Server:** $SonarHostUrl

---

## Quality Gate

| Metrik | Wert |
| ------ | ---- |
| Status | **$QgStatus** |

---

## Findings

**Offene Issues gesamt:** $TotalIssues

| Qualitaet | Offene Issues |
| --------- | ------------- |
| Security | $SecCount |
| Reliability | $RelCount |
| Maintainability | $MaintCount |

### Verteilung nach Schweregrad

| Schweregrad | Anzahl |
| ----------- | ------ |
"@

foreach ($Group in $SeverityGroups) {
    $SummaryMarkdown += "`n| $($Group.Name) | $($Group.Count) |"
}

$SummaryMarkdown += @"


### Top 5 Regelverstoesse

| Regel | Anzahl |
| ----- | ------ |
"@

foreach ($Group in $RuleGroups) {
    $SummaryMarkdown += "`n| $($Group.Name) | $($Group.Count) |"
}

$SummaryMarkdown += @"


---

## Testabdeckung

| Metrik | Wert |
| ------ | ---- |
| Coverage % | $CoveragePct |
| Zu deckende Zeilen | $LinesToCover |
| Nicht gedeckte Zeilen | $UncoveredLines |

---

## Duplikate

| Metrik | Wert |
| ------ | ---- |
| Duplikatdichte % | $DupDensity |
| Duplizierte Zeilen | $DupLines |
| Duplizierte Bloecke | $DupBlocks |
| Duplizierte Dateien | $DupFiles |
"@

$SummaryMarkdown | Out-File -FilePath $SummaryFile -Encoding utf8

# 6. Details
$DetailsMarkdown = @"
# SonarQube Findings im Detail

**Projekt:** $ProjectKey
**Zeitpunkt:** $Timestamp
**Offene Issues:** $TotalIssues

---

| Status | Regel | Schweregrad | Datei | Zeile | Meldung |
| ------ | ----- | ----------- | ----- | ----- | ------- |
"@

if ($IssuesData -and $IssuesData.issues) {
    foreach ($Issue in $IssuesData.issues) {
        $CleanFile = $Issue.component -replace "^${ProjectKey}:", ""
        if ($CleanFile -match ":(.+)$") {
            $CleanFile = $Matches[1]
        }
        $Line = if ($Issue.line) { $Issue.line } else { "-" }
        $Severity = if ($Issue.severity) { $Issue.severity } else { "UNKNOWN" }
        $Message = $Issue.message -replace '\|', '\|'
        $DetailsMarkdown += "`n| $($Issue.status) | ``$($Issue.rule)`` | **$Severity** | ``$CleanFile`` | $Line | $Message |"
    }
}

$DetailsMarkdown += "`n"
$DetailsMarkdown | Out-File -FilePath $DetailsFile -Encoding utf8

# 7. Alte Berichte entfernen, nur der letzte Lauf bleibt
Get-ChildItem -Path $OutputDir -File -Filter "*_sonar_summary.md" |
    Where-Object { $_.FullName -ne $SummaryFile } |
    Remove-Item -Force
Get-ChildItem -Path $OutputDir -File -Filter "*_sonar_details.md" |
    Where-Object { $_.FullName -ne $DetailsFile } |
    Remove-Item -Force

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "Scan und Berichte abgeschlossen." -ForegroundColor Green
Write-Host "Quality Gate: $QgStatus" -ForegroundColor Green
Write-Host "Offene Issues: $TotalIssues" -ForegroundColor Green
Write-Host "Summary: $SummaryFile" -ForegroundColor Green
Write-Host "Details: $DetailsFile" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
