$ErrorActionPreference = 'Stop'

$configPath = Join-Path $HOME '.copilot\mcp-config.json'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "MCP-Konfiguration nicht gefunden: $configPath"
}

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$server = $config.mcpServers.homeassistant
if (-not $server) {
    throw "Der Server 'homeassistant' fehlt in der MCP-Konfiguration."
}
if ([string]::IsNullOrWhiteSpace($server.command)) {
    throw "Für den Server 'homeassistant' ist kein Startbefehl konfiguriert."
}
if ([string]::IsNullOrWhiteSpace($server.env.HOMEASSISTANT_URL)) {
    throw 'HOMEASSISTANT_URL fehlt in der MCP-Konfiguration.'
}
if ([string]::IsNullOrWhiteSpace($server.env.HOMEASSISTANT_TOKEN)) {
    throw 'HOMEASSISTANT_TOKEN fehlt in der MCP-Konfiguration.'
}

$serverArgs = @($server.args)
$previousUrl = [Environment]::GetEnvironmentVariable('HOMEASSISTANT_URL', 'Process')
$previousToken = [Environment]::GetEnvironmentVariable('HOMEASSISTANT_TOKEN', 'Process')

try {
    [Environment]::SetEnvironmentVariable('HOMEASSISTANT_URL', $server.env.HOMEASSISTANT_URL, 'Process')
    [Environment]::SetEnvironmentVariable('HOMEASSISTANT_TOKEN', $server.env.HOMEASSISTANT_TOKEN, 'Process')

    & $server.command @serverArgs
}
finally {
    [Environment]::SetEnvironmentVariable('HOMEASSISTANT_URL', $previousUrl, 'Process')
    [Environment]::SetEnvironmentVariable('HOMEASSISTANT_TOKEN', $previousToken, 'Process')
}