# Epic: Codequalität und SAST

## Ziel

Die Python-Komponenten des Projekts werden statisch auf Sicherheits-,
Zuverlässigkeits- und Wartbarkeitsprobleme geprüft. Grundlage ist ein
SonarQube-Server im Heimnetz. Die Prüfung ist reproduzierbar, läuft lokal und
liefert einen lesbaren Bericht.

## Architektur

- SonarQube unter `http://sonar.srv001`, Projekt-Key `HAD`.
- Scan über die SonarScanner-CLI, gestartet durch
  `tests/sast/run-sonar-scan.ps1`.
- Testabdeckung aus `coverage.xml` (pytest und coverage.py).
- Berichte lokal unter `tests/sast/reports/`, von Git ausgeschlossen.
- Token ausschließlich in `.env` (gitignoriert) oder als Parameter.

## Abgrenzung

- Keine CI/CD-Anbindung und kein automatischer Scan bei jedem Commit.
- Keine Analyse von Dokumentation, Deployment-Vorlagen oder Spezifikationen.
- Keine Veröffentlichung des SonarQube-Servers im Internet.

## Qualitätsziel

- 0 offene Issues.
- 0 Duplikate.
- Bestandenes Quality Gate.
- Testabdeckung wird berichtet, ist aber kein hartes Gate.

## Prozess

Der Scan läuft nach dem UAT- und Freigabeschritt. Der Ablauf ist in
`DEV Prompt.md` festgehalten.
