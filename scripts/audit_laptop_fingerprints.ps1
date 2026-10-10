param([Parameter(Mandatory=$true)][string]$Kit, [Parameter(Mandatory=$true)][string]$Run)
$ErrorActionPreference = 'Stop'
$kitPath = (Resolve-Path -LiteralPath $Kit).Path
$runPath = (Resolve-Path -LiteralPath $Run).Path
. (Join-Path $kitPath 'engine\runner.ps1') -LibraryOnly -KitRoot $kitPath
$script:LocalRun = $runPath
$environment = Read-Json (Join-Path $runPath 'environment.json')
$script:Fingerprint = Text-Hash (Json $environment.identity)
if ($script:Fingerprint -ne $environment.fingerprint) { throw 'Environment fingerprint mismatch' }
$plan = Read-Json (Join-Path $runPath 'plan.json')
$count = 0
foreach ($case in $plan.Full) {
    $record = Read-Success $case
    if ($null -eq $record) { throw "Missing case: $($case.id)" }
    $count++
}
if ($count -ne 430) { throw "Unexpected record count: $count" }
Write-Output "PASS: environment and $count case fingerprints; all recorded artifact hashes verified."
