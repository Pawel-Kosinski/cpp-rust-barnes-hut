#requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$Kit, [Parameter(Mandatory=$true)][string]$TestRoot)
$ErrorActionPreference = 'Stop'
$Kit = [IO.Path]::GetFullPath($Kit)
$TestRoot = [IO.Path]::GetFullPath($TestRoot)
. (Join-Path $PSScriptRoot 'runner.ps1') -KitRoot $Kit -LibraryOnly
Add-Type -Path (Join-Path $PSScriptRoot 'runtime.cs')
$script:Mode = 'Smoke'
$script:LocalRun = Join-Path $TestRoot 'local'
$script:SyncRun = Join-Path $TestRoot 'sync'
$script:HostRoot = $script:SyncRun
$script:StopFile = Join-Path $script:SyncRun 'STOP.request'
$script:PowerScheme = Power-Scheme
$script:PowerSettingsHash = Text-Hash (Power-Details)
$script:Fingerprint = Text-Hash 'AUTOMATED_TEST_NOT_LAPTOP_SCIENTIFIC_DATA'
$script:Job = [LaptopRuntime]::NewJob()
[IO.Directory]::CreateDirectory($script:LocalRun) | Out-Null
[IO.Directory]::CreateDirectory($script:SyncRun) | Out-Null
$script:Tests = New-Object 'Collections.Generic.List[string]'
function Assert([bool]$Value, [string]$Name) {
    if (!$Value) { throw "FAILED: $Name" }
    $script:Tests.Add($Name)
    Write-Host "PASS $Name"
}
function Throws([scriptblock]$Action, [string]$Name) {
    $raised = $false
    try { & $Action | Out-Null } catch { $raised = $true }
    Assert $raised $Name
}
try {
    $profile = [pscustomobject]@{declared_armoury_mode='Performance'; reject_power_scheme_guids=@('6fecc5ae-f350-48a5-b669-b472cb895ccf')}
    Throws { Check-ExperimentProfile $profile 'Power Scheme GUID: 6fecc5ae-f350-48a5-b669-b472cb895ccf (renamed)' } 'old Turbo GUID rejected even if renamed'
    Throws { Check-ExperimentProfile $profile 'Power Scheme GUID: 00000000-0000-0000-0000-000000000000 (Turbo)' } 'Turbo label rejected on another GUID'
    Check-ExperimentProfile $profile 'Power Scheme GUID: 00000000-0000-0000-0000-000000000000 (Performance)'
    Assert $true 'non-Turbo plan allowed subject to operator mode confirmation'
    $plan = Read-Json (Join-Path $Kit 'plan.json')
    Assert ($plan.Full.Count -eq 430 -and $plan.Smoke.Count -eq 10) 'plan counts'
    Assert (@($plan.Full | Where-Object threads -gt 8).Count -eq 0) 'no oversubscription above 8 threads'
    Assert (@($plan.Full | Group-Object id | Where-Object Count -gt 1).Count -eq 0) 'unique case ids'
    Throws { Safe-Path $TestRoot '..\escape' } 'path traversal rejected'
    $m = Metrics "Tree construction time: 1 ms`nForce/update time: 2 ms`nCleanup time: 0 ms`nTotal measured time: 6 ms`nForce kernel time: 1.5 ms`nState update time: 0.5 ms" 2
    Assert ($m.total_ms -eq 3) 'total normalized by measured frames'
    Throws { Metrics 'garbled output' 1 } 'missing metrics rejected'
    $integrity = Join-Path $TestRoot 'integrity'
    Write-Atomic (Join-Path $integrity 'a.txt') 'original'
    $smallManifest = [pscustomobject]@{files=@([pscustomobject]@{path='a.txt'; sha256=(Hash (Join-Path $integrity 'a.txt'))})}
    Verify-Payload $integrity $smallManifest
    Write-Atomic (Join-Path $integrity 'a.txt') 'modified'
    Throws { Verify-Payload $integrity $smallManifest } 'modified payload rejected'

    $lockPath = Join-Path $TestRoot 'concurrency.lock'
    $lock = [IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None')
    try { Throws { [IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None') } 'concurrent lock rejected' }
    finally { $lock.Dispose() }

    # Reproduce a cloud-drive reader which permits writes but denies replacement.
    $mirrorName = 'mirror-fixture.txt'
    $mirrorSource = Join-Path $script:LocalRun $mirrorName
    $mirrorTarget = Join-Path $script:SyncRun $mirrorName
    Write-Atomic $mirrorSource 'new contents'
    Write-Atomic $mirrorTarget 'old contents'
    $cloudReader = [IO.File]::Open($mirrorTarget, 'Open', 'Read', [IO.FileShare]::ReadWrite)
    try {
        Mirror $mirrorName
        Assert ((Hash $mirrorSource) -eq (Hash $mirrorTarget)) 'overwrite fallback works when cloud reader denies delete'
        Assert ($script:PendingMirrors.Count -eq 0) 'fallback does not leave pending work'
    } finally { $cloudReader.Dispose() }
    Write-Atomic $mirrorSource 'next contents'
    $cloudLock = [IO.File]::Open($mirrorTarget, 'Open', 'Read', 'None')
    try {
        Mirror $mirrorName
        Assert ($script:PendingMirrors.ContainsKey($mirrorName)) 'exclusive cloud lock queues mirror instead of failing'
        Assert ((Get-Content -LiteralPath $mirrorSource -Raw) -eq 'next contents') 'local source survives locked mirror'
        $script:PendingMirrors = @{}
        Restore-MirrorQueue
        Assert ($script:PendingMirrors.ContainsKey($mirrorName)) 'mirror queue survives launcher restart'
        $duringLock = Json $plan.Smoke[0] | ConvertFrom-Json
        $duringLock.id = 'solver-despite-cloud-lock'
        $r = Invoke-Case $duringLock $Kit
        Assert ($r.state -eq 'success') 'solver completes despite an unrelated locked mirror'
    } finally { $cloudLock.Dispose() }
    Flush-Mirrors
    Assert ($script:PendingMirrors.Count -eq 0) 'deferred mirror drains after unlock'
    Assert ((Hash $mirrorSource) -eq (Hash $mirrorTarget)) 'deferred mirror delivers exact bytes'

    Status 'running' 'initial status'
    $latestPath = Join-Path $script:HostRoot 'latest.json'
    $latestLock = [IO.File]::Open($latestPath, 'Open', 'Read', 'None')
    try {
        Status 'running' 'status during cloud lock'
        Assert ($script:PendingMirrors.ContainsKey('@latest')) 'locked latest status does not abort computation'
        Assert ((Read-Json (Join-Path $script:LocalRun 'status.json')).detail -eq 'status during cloud lock') 'local status stays current while mirror is locked'
    } finally { $latestLock.Dispose() }
    Flush-Mirrors
    Assert ((Read-Json $latestPath).detail -eq 'status during cloud lock') 'latest status catches up after unlock'
    Assert ($script:PendingMirrors.Count -eq 0) 'status mirror queue drains'

    # Exercise all scientific correctness gates, never count these as laptop measurements.
    foreach ($c in $plan.Full | Where-Object group -eq 'correctness') {
        $r = Invoke-Case $c $Kit
        Assert ($r.state -eq 'success' -and $r.accuracy.regression_passed) ('force check '+$c.id)
    }
    $c = $plan.Smoke[0]
    $r = Invoke-Case $c $Kit
    $recordPath = Join-Path $script:LocalRun ('records\'+$c.id+'.json')
    $savedHash = Hash $recordPath
    $cached = Read-Success $c
    Assert ($cached.state -eq 'success' -and (Hash $recordPath) -eq $savedHash) 'resume reads result without rewriting'
    $different = Json $c | ConvertFrom-Json
    $different.threads = 2
    Throws { Read-Success $different } 'changed case rejected'
    $originalFingerprint = $script:Fingerprint
    $script:Fingerprint = 'different-machine'
    Throws { Read-Success $c } 'changed environment rejected'
    $script:Fingerprint = $originalFingerprint
    $artifactName = @($cached.artifacts.PSObject.Properties)[0].Name
    $artifact = Safe-Path $script:LocalRun $artifactName
    $bytes = [IO.File]::ReadAllBytes($artifact)
    Write-Atomic $artifact 'changed'
    Throws { Read-Success $c } 'damaged cached output rejected'
    [IO.File]::WriteAllBytes($artifact, $bytes)

    $fakePayload = Join-Path $TestRoot 'fake payload'
    [IO.Directory]::CreateDirectory((Join-Path $fakePayload 'bin')) | Out-Null
    Write-Atomic (Join-Path $fakePayload 'input.txt') '1 2 3 4 5'
    $fakeExe = Join-Path $fakePayload 'bin\fake.exe'
    Add-Type -TypeDefinition @'
using System;
class FakeSolver {
    static int Main(string[] args) {
        string theta = args[Array.IndexOf(args, "--theta")+1];
        if (theta == "fail") { Console.Error.WriteLine("intentional failure"); return 7; }
        if (theta == "sleep") { Console.WriteLine("before sleep"); System.Threading.Thread.Sleep(60000); }
        Console.WriteLine("Tree construction time: 1 ms\nForce/update time: 2 ms\nCleanup time: 0 ms\nTotal measured time: 3 ms\nForce kernel time: 1.5 ms\nState update time: 0.5 ms");
        return 0;
    }
}
'@ -OutputAssembly $fakeExe -OutputType ConsoleApplication
    $fake = [pscustomobject]@{id='failure'; solver='fake'; group='smoke'; input='input.txt'; frames=1; warmup=0;
        theta='fail'; threads=1; timeout_seconds=1}
    Throws { Invoke-Case $fake $fakePayload } 'nonzero exit stops case'
    $attempt = Get-ChildItem -LiteralPath (Join-Path $script:LocalRun 'attempts\failure') -Directory | Select-Object -Last 1
    $failed = Read-Json (Join-Path $attempt.FullName 'process.json')
    Assert ($failed.returncode -eq 7 -and $failed.state -eq 'failed') 'failure exit code retained'
    Assert ((Get-Content -LiteralPath (Join-Path $attempt.FullName 'stderr.log') -Raw) -match 'intentional failure') 'stderr retained'
    $fake.id = 'timeout'; $fake.theta = 'sleep'
    Throws { Invoke-Case $fake $fakePayload } 'timeout stops process'
    $attempt = Get-ChildItem -LiteralPath (Join-Path $script:LocalRun 'attempts\timeout') -Directory | Select-Object -Last 1
    $failed = Read-Json (Join-Path $attempt.FullName 'process.json')
    Assert ($failed.error -match 'timeout') 'timeout reason retained'
    Assert ($null -eq (Get-Process -Id $failed.pid -ErrorAction SilentlyContinue)) 'timed-out child not left running'
    $fake.id = 'stopped'; $fake.timeout_seconds = 60
    Write-Atomic $script:StopFile 'STOP'
    Throws { Invoke-Case $fake $fakePayload } 'stop request interrupts active child'
    Remove-Item -LiteralPath $script:StopFile
    $fake.theta = '0.3'
    $r = Invoke-Case $fake $fakePayload
    Assert ($r.state -eq 'success') 'stopped case can be retried'
    Assert (@(Get-ChildItem -LiteralPath (Join-Path $script:LocalRun 'attempts\stopped') -Directory).Count -eq 2) 'old failed attempt retained'

    $job = [LaptopRuntime]::NewJob()
    $p = New-Object Diagnostics.Process
    $p.StartInfo.FileName = $fakeExe
    $p.StartInfo.Arguments = '--theta sleep'
    $p.StartInfo.UseShellExecute = $false
    $p.StartInfo.CreateNoWindow = $true
    $null = $p.Start()
    [LaptopRuntime]::Attach($job, $p.Handle)
    [LaptopRuntime]::CloseJob($job)
    Assert ($p.WaitForExit(5000)) 'closing job kills child'
    $p.Dispose()
    Save-Json (Join-Path $TestRoot 'test-report.json') ([ordered]@{passed=$true; count=$script:Tests.Count;
        tests=@($script:Tests.ToArray()); purpose='workstation kit verification, not laptop scientific data'})
    Write-Host "ALL $($script:Tests.Count) TESTS PASSED"
} finally { [LaptopRuntime]::CloseJob($script:Job) }
