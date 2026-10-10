#requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$SourceKit,
      [Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $SourceKit).Path
$target = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $target) { throw 'Destination exists; never overwrite a deployed kit.' }
$utf8 = New-Object Text.UTF8Encoding($false)
function Digest([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function SaveJson([string]$Path, $Value) {
    [IO.File]::WriteAllText($Path, (ConvertTo-Json -InputObject $Value -Depth 30) + "`n", $utf8)
}
$manifestPath = Join-Path $source 'kit-manifest.json'
$expected = '0c87ef6469e8150fb59ffe8df9dffc3052368e0dbbb73dbc73985f9b8ab8041b'
if ((Digest $manifestPath) -ne $expected) { throw 'Use the verified completed Turbo-labelled campaign kit.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($file in $manifest.files) {
    $path = [IO.Path]::GetFullPath((Join-Path $source $file.path))
    if (!$path.StartsWith($source.TrimEnd('\')+'\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe manifest path' }
    if ((Digest $path) -ne $file.sha256 -or (Get-Item -LiteralPath $path).Length -ne $file.bytes) { throw "Source changed: $path" }
}
New-Item -ItemType Directory -Path $target | Out-Null
foreach ($file in $manifest.files) {
    $out = Join-Path $target $file.path
    New-Item -ItemType Directory -Path (Split-Path -Parent $out) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $source $file.path) -Destination $out
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'runner.ps1') -Destination (Join-Path $target 'engine\runner.ps1')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'PERFORMANCE_START_HERE.txt') -Destination (Join-Path $target 'START_HERE.txt')
SaveJson (Join-Path $target 'provenance\comparison-profile.json') ([ordered]@{
    parent_kit_manifest_sha256=$expected; comparison='same 430 cases and exact plan order; separate operator-declared Performance run';
    unchanged='all executable bytes, DLLs, inputs, reference files and plan.json';
    prior_evidence='Windows power plan named Turbo recorded at preflight; Armoury Crate mode not independently observed';
    temperature_frequency_telemetry=$false; original_data_replaced=$false})
$files = @(Get-ChildItem -LiteralPath $target -Recurse -File | Sort-Object FullName | ForEach-Object {
    [ordered]@{path=$_.FullName.Substring($target.Length+1).Replace('\','/'); sha256=(Digest $_.FullName); bytes=$_.Length}
})
$result = [ordered]@{schema=1; kit='BHBench-CR-laptop-Performance-2026-10-09'; runner_revision='profile-guard-1';
    target_cpu='Intel Core i7-11370H'; full_processes=430; smoke_processes=10;
    experiment=[ordered]@{label='Performance-repeat'; declared_armoury_mode='Performance';
        reject_power_scheme_guids=@('6fecc5ae-f350-48a5-b669-b472cb895ccf')}; files=$files}
SaveJson (Join-Path $target 'kit-manifest.json') $result
$lines = @($files | ForEach-Object { $_.sha256 + '  ' + $_.path })
$lines += (Digest (Join-Path $target 'kit-manifest.json')) + '  kit-manifest.json'
[IO.File]::WriteAllText((Join-Path $target 'SHA256SUMS.txt'), ($lines -join "`n")+"`n", $utf8)
if ((Digest (Join-Path $target 'plan.json')) -ne (Digest (Join-Path $source 'plan.json'))) { throw 'Plan changed' }
foreach ($folder in @('bin','inputs','references')) {
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $source $folder) -File) {
        if ((Digest $file.FullName) -ne (Digest (Join-Path $target ($folder+'\'+$file.Name)))) { throw "Changed scientific artifact: $($file.Name)" }
    }
}
Write-Output ('READY: '+$target)
Write-Output ('Manifest SHA256: '+(Digest (Join-Path $target 'kit-manifest.json')))
Write-Output 'Verified: identical 430-case plan, solvers, DLLs, inputs and references; separate result namespace.'
