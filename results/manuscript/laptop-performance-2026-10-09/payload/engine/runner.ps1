#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Full','Smoke','Status','Stop')][string]$Mode = 'Smoke',
    [string]$KitRoot = '',
    [string]$LocalRoot = (Join-Path $env:LOCALAPPDATA 'BHBench-CR\laptop-r1'),
    [switch]$LibraryOnly
)
if (!$KitRoot) { $KitRoot = Split-Path -Parent $PSScriptRoot }
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:Culture = [Globalization.CultureInfo]::InvariantCulture
$script:LocalRun = $null
$script:SyncRun = $null
$script:Done = 0
$script:Total = 0
$script:Current = ''
$script:Lock = $null
$script:Job = [IntPtr]::Zero
$script:Fingerprint = ''
$script:PendingMirrors = @{}

function Json($Value) { ConvertTo-Json -InputObject $Value -Depth 30 -Compress }
function Read-Json([string]$Path) { Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Text-Hash([string]$Value) {
    $h = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($h.ComputeHash($script:Utf8.GetBytes($Value)))).Replace('-','').ToLowerInvariant() }
    finally { $h.Dispose() }
}
function Write-Atomic([string]$Path, [string]$Value) {
    [IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null
    $temp = "$Path.$PID.tmp"
    [IO.File]::WriteAllText($temp, $Value, $script:Utf8)
    if ([IO.File]::Exists($Path)) { [IO.File]::Replace($temp, $Path, [System.Management.Automation.Language.NullString]::Value) }
    else { [IO.File]::Move($temp, $Path) }
}
function Save-Json([string]$Path, $Value) { Write-Atomic $Path (Json $Value) }
function Safe-Path([string]$Root, [string]$Relative) {
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $path = [IO.Path]::GetFullPath((Join-Path $Root $Relative))
    if (!$path.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escapes its root' }
    return $path
}
function Publish-Copy([string]$Source, [string]$Target, [int]$Attempts = 2) {
    $temp = "$Target.$PID.tmp"
    for ($try = 0; $try -lt $Attempts; $try++) {
        try {
            [IO.Directory]::CreateDirectory((Split-Path -Parent $Target)) | Out-Null
            [IO.File]::Copy($Source, $temp, $true)
            try {
                if ([IO.File]::Exists($Target)) { [IO.File]::Replace($temp, $Target, [System.Management.Automation.Language.NullString]::Value) }
                else { [IO.File]::Move($temp, $Target) }
            } catch {
                $cause = $_.Exception.GetBaseException()
                if ($cause -isnot [IO.IOException] -and $cause -isnot [UnauthorizedAccessException]) { throw }
                # Synology may deny rename/delete but allow overwrite. Only the mirror
                # uses this non-atomic fallback; authoritative local records stay atomic.
                [IO.File]::Copy($Source, $Target, $true)
            }
            return $null
        } catch {
            $cause = $_.Exception.GetBaseException()
            if ($cause -isnot [IO.IOException] -and $cause -isnot [UnauthorizedAccessException]) { throw }
            if ($try -eq $Attempts-1) { return $cause.Message }
            Start-Sleep -Milliseconds 150
        } finally {
            try { if ([IO.File]::Exists($temp)) { [IO.File]::Delete($temp) } } catch { }
        }
    }
}
function Save-MirrorQueue {
    Save-Json (Join-Path $script:LocalRun 'mirror-pending.json') ([ordered]@{
        files=@($script:PendingMirrors.Keys | Sort-Object); errors=$script:PendingMirrors})
}
function Mirror([string]$Relative, [switch]$HostLatest, [int]$Attempts = 2) {
    $source = Safe-Path $script:LocalRun $Relative
    if ($HostLatest) {
        if ($Relative -ne 'status.json') { throw 'Only status.json can be published as latest.json' }
        $key = '@latest'
        $target = Safe-Path $script:HostRoot 'latest.json'
    } else {
        $key = $Relative
        $target = Safe-Path $script:SyncRun $Relative
    }
    $failure = Publish-Copy $source $target $Attempts
    if ($null -eq $failure) {
        if ($script:PendingMirrors.ContainsKey($key)) { $script:PendingMirrors.Remove($key); Save-MirrorQueue }
    } else {
        if (!$script:PendingMirrors.ContainsKey($key)) {
            $line = '{0} SYNC DEFERRED: {1}: {2}' -f [DateTime]::UtcNow.ToString('o'), $key, $failure
            Write-Host $line -ForegroundColor Yellow
            [IO.File]::AppendAllText((Join-Path $script:LocalRun 'sync-warnings.log'), "$line`r`n", $script:Utf8)
        }
        $script:PendingMirrors[$key] = $failure
        Save-MirrorQueue
    }
}
function Flush-Mirrors([int]$Limit = 32) {
    foreach ($key in @($script:PendingMirrors.Keys | Sort-Object | Select-Object -First $Limit)) {
        if ($key -eq '@latest') { Mirror 'status.json' -HostLatest -Attempts 1 }
        else { Mirror $key -Attempts 1 }
    }
    if (Test-Path -LiteralPath (Join-Path $script:LocalRun 'sync-warnings.log')) { Mirror 'sync-warnings.log' -Attempts 1 }
}
function Restore-MirrorQueue {
    $path = Join-Path $script:LocalRun 'mirror-pending.json'
    if (Test-Path -LiteralPath $path) {
        foreach ($key in (Read-Json $path).files) {
            if ($key -ne '@latest') {
                $null = Safe-Path $script:LocalRun $key
                $null = Safe-Path $script:SyncRun $key
            }
            $script:PendingMirrors[$key] = 'Pending from previous invocation'
        }
    }
}
function Log([string]$Message) {
    $line = '{0} {1}' -f [DateTime]::UtcNow.ToString('o'), $Message
    Write-Host $line
    if ($script:LocalRun) {
        [IO.File]::AppendAllText((Join-Path $script:LocalRun 'runner.log'), "$line`r`n", $script:Utf8)
        Mirror 'runner.log'
    }
}
function Status([string]$State, [string]$Detail = '') {
    $value = [ordered]@{state=$State; mode=$Mode; host=$env:COMPUTERNAME;
        updated_utc=[DateTime]::UtcNow.ToString('o'); completed=$script:Done; total=$script:Total;
        current_case=$script:Current; detail=$Detail; local_path=$script:LocalRun;
        synced_path=$script:SyncRun; launcher_pid=$PID; mirror_pending_files=$script:PendingMirrors.Count}
    Save-Json (Join-Path $script:LocalRun 'status.json') $value
    Mirror 'status.json'
    Mirror 'status.json' -HostLatest
}
function Power-Scheme {
    $text = (& "$env:SystemRoot\System32\powercfg.exe" /getactivescheme | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read active power scheme' }
    return $text
}
function Check-ExperimentProfile($Experiment, [string]$Scheme) {
    foreach ($guid in $Experiment.reject_power_scheme_guids) {
        if ($Scheme -match [regex]::Escape($guid)) {
            throw 'Still using the recorded Turbo power plan. Connect AC first, then choose Performance in Armoury Crate. No settings were changed by this script.'
        }
    }
    if ($Experiment.declared_armoury_mode -eq 'Performance' -and $Scheme -match '(?i)\bturbo\b') {
        throw 'Windows still reports Turbo. Select Performance after connecting AC, then retry.'
    }
}
function Check-Power {
    if ($Mode -ne 'Full') { return }
    $power = [LaptopRuntime]::Power()
    if ($power.ACLineStatus -ne 1 -or $power.SystemStatusFlag -eq 1) {
        throw 'PAUSED: Connect AC power and disable battery saver, then start again.'
    }
}
function Power-Details {
    # /query includes the active overlay, per Microsoft's powercfg documentation.
    $value = (& "$env:SystemRoot\System32\powercfg.exe" /query | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read power settings' }
    return $value
}
function Check-PowerConfiguration {
    if ((Power-Scheme) -ne $script:PowerScheme -or (Text-Hash (Power-Details)) -ne $script:PowerSettingsHash) {
        throw 'Power settings changed; results must not be mixed.'
    }
}
function Process-Snapshot {
    $rows = foreach ($p in Get-Process) {
        try {
            [pscustomobject]@{name=$p.ProcessName; pid=$p.Id; cumulative_cpu_seconds=$p.TotalProcessorTime.TotalSeconds}
        } catch { continue } # Protected system services may deny access to their counters.
    }
    return @($rows | Sort-Object cumulative_cpu_seconds -Descending | Select-Object -First 15)
}
function Metrics([string]$Text, [int]$Frames) {
    $labels = [ordered]@{tree_ms='Tree construction time'; force_update_ms='Force/update time';
        cleanup_ms='Cleanup time'; total_ms='Total measured time'; kernel_ms='Force kernel time'; update_ms='State update time'}
    $result = [ordered]@{}
    foreach ($key in $labels.Keys) {
        $m = [regex]::Match($Text, '(?m)^'+[regex]::Escape($labels[$key])+':\s*([0-9.eE+-]+)\s+ms')
        if (!$m.Success) { throw "Missing timing: $key" }
        $v = [double]::Parse($m.Groups[1].Value, $script:Culture)
        if ($v -lt 0 -or [double]::IsInfinity($v) -or [double]::IsNaN($v)) { throw "Invalid timing: $key" }
        if ($key -eq 'total_ms') { $v /= $Frames }
        $result[$key] = $v
    }
    $sum = $result.tree_ms + $result.force_update_ms + $result.cleanup_ms
    if ([math]::Abs($sum-$result.total_ms) -gt [math]::Max(0.01, $sum*1e-4)) { throw 'Timing sum mismatch' }
    $force = $result.kernel_ms + $result.update_ms
    if ([math]::Abs($force-$result.force_update_ms) -gt [math]::Max(0.01, $force*1e-4)) { throw 'Kernel/update sum mismatch' }
    return $result
}
function Quote-Argument([string]$Value) {
    # CommandLineToArgvW-compatible quoting, including a trailing backslash.
    return '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}
function Relative-Path([string]$Base, [string]$Path) {
    $baseUri = New-Object Uri([IO.Path]::GetFullPath($Base).TrimEnd('\')+'\')
    $pathUri = New-Object Uri([IO.Path]::GetFullPath($Path))
    return [Uri]::UnescapeDataString($baseUri.MakeRelativeUri($pathUri).ToString()).Replace('/','\')
}
function Case-Fingerprint($Case) { Text-Hash ($script:Fingerprint + (Json $Case)) }
function Read-Success($Case) {
    $path = Join-Path $script:LocalRun ('records\'+$Case.id+'.json')
    if (!(Test-Path -LiteralPath $path)) { return $null }
    $record = Read-Json $path
    if ($record.fingerprint -ne (Case-Fingerprint $Case) -or $record.state -ne 'success') {
        throw "Changed case identity: $($Case.id)"
    }
    foreach ($entry in $record.artifacts.PSObject.Properties) {
        $artifact = Safe-Path $script:LocalRun $entry.Name
        if (!(Test-Path -LiteralPath $artifact) -or (Hash $artifact) -ne $entry.Value) {
            throw "Cached result damaged: $artifact. Do not delete it; retain it for diagnosis."
        }
    }
    return $record
}
function Invoke-Case($Case, [string]$Payload) {
    Check-Power
    Check-PowerConfiguration
    $attempt = 'attempts\{0}\{1}-{2}' -f $Case.id, [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff'), $PID
    $dir = Safe-Path $script:LocalRun $attempt
    [IO.Directory]::CreateDirectory($dir) | Out-Null
    $binary = Safe-Path $Payload ('bin\'+$Case.solver+'.exe')
    $inputFile = Safe-Path $Payload $Case.input
    # Relative ASCII CLI paths also work with a Unicode Windows account/cache path.
    $words = @('--input', (Relative-Path $Payload $inputFile), '--frames', [string]$Case.frames, '--warmup-frames', [string]$Case.warmup,
        '--theta', [string]$Case.theta, '--threads', [string]$Case.threads, '--dt', '0.016')
    if ($Case.group -eq 'correctness') { $words += @('--dump-forces', (Relative-Path $Payload (Join-Path $dir 'forces.csv'))) }
    $record = [ordered]@{fingerprint=(Case-Fingerprint $Case); case=$Case; state='running';
        started_utc=[DateTime]::UtcNow.ToString('o'); command=@($binary)+$words;
        cwd=$Payload; input_sha256=(Hash $inputFile); executable_sha256=(Hash $binary);
        environment_fingerprint=$script:Fingerprint; returncode=$null; error=$null}
    Save-Json (Join-Path $dir 'process.json') $record
    Mirror ($attempt+'\process.json')
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $binary
    $start.Arguments = ($words | ForEach-Object { Quote-Argument $_ }) -join ' '
    $start.WorkingDirectory = $Payload
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    # Match the recorded Ryzen default runtime policy, independent of shell overrides.
    foreach ($key in @($start.EnvironmentVariables.Keys)) {
        if ($key -match '^(OMP_|GOMP_|KMP_|RAYON_)') { $start.EnvironmentVariables.Remove($key) }
    }
    $start.EnvironmentVariables['PATH'] = (Join-Path $Payload 'bin')+';'+$env:SystemRoot+'\System32;'+$env:SystemRoot
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    $outFile = [IO.File]::Create((Join-Path $dir 'stdout.log'))
    $errFile = [IO.File]::Create((Join-Path $dir 'stderr.log'))
    $outTask = $null; $errTask = $null; $started = $false
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $failure = $null
    try {
        $started = $process.Start()
        if (!$started) { throw 'Process did not start' }
        [LaptopRuntime]::Attach($script:Job, $process.Handle)
        $record['pid'] = $process.Id
        $outTask = $process.StandardOutput.BaseStream.CopyToAsync($outFile)
        $errTask = $process.StandardError.BaseStream.CopyToAsync($errFile)
        $lastHeartbeat = 0.0
        while (!$process.WaitForExit(1000)) {
            if (Test-Path -LiteralPath $script:StopFile) { throw 'PAUSED: User requested stop; interrupted attempt will be rerun.' }
            Check-Power
            if ($watch.Elapsed.TotalSeconds -gt $Case.timeout_seconds) { throw "Process timeout after $($Case.timeout_seconds) seconds" }
            if ($watch.Elapsed.TotalSeconds - $lastHeartbeat -ge 30) {
                Status 'running' ('Current process elapsed: {0:N0} s' -f $watch.Elapsed.TotalSeconds)
                $lastHeartbeat = $watch.Elapsed.TotalSeconds
            }
        }
        $record.returncode = $process.ExitCode
        if ($process.ExitCode -ne 0) { throw "Solver exited with code $($process.ExitCode); see stderr.log" }
        Check-Power
        Check-PowerConfiguration
    } catch { $failure = $_ }
    finally {
        if ($started -and !$process.HasExited) { $process.Kill(); $process.WaitForExit() }
        if ($outTask) { $null = $outTask.GetAwaiter().GetResult() }
        if ($errTask) { $null = $errTask.GetAwaiter().GetResult() }
        $outFile.Dispose(); $errFile.Dispose(); $process.Dispose()
        $watch.Stop()
    }
    try {
        if ($failure) { throw $failure }
        $record['metrics'] = Metrics ([IO.File]::ReadAllText((Join-Path $dir 'stdout.log'))) $Case.frames
        if ($Case.group -eq 'correctness') {
            $v = [LaptopRuntime]::Forces((Safe-Path $Payload $Case.reference), (Join-Path $dir 'forces.csv'))
            if ($v[0] -ne $Case.n) { throw 'Incorrect number of acceleration samples' }
            # This is a cross-host regression gate, not an astrophysical accuracy bound.
            $allowed = [math]::Max(1e-6, 0.01 * $Case.expected_rms)
            if ($Case.solver -match '_v1$') { $passed = $v[1] -le 1e-4 }
            else { $passed = [math]::Abs($v[1]-$Case.expected_rms) -le $allowed }
            $record['accuracy'] = [ordered]@{samples=$v[0]; rms_relative=$v[1]; p95_particle_relative=$v[2];
                max_particle_relative=$v[3]; expected_ryzen_rms=$Case.expected_rms; regression_passed=$passed}
            if (!$passed) { throw 'Force regression differs from the reference campaign; inspect before timing.' }
        }
        $record.state = 'success'
    } catch {
        $failure = $_
        $record.state = 'failed'
        $record.error = $_.Exception.Message
    }
    $record['wall_seconds'] = $watch.Elapsed.TotalSeconds
    $record['completed_utc'] = [DateTime]::UtcNow.ToString('o')
    $artifacts = [ordered]@{}
    foreach ($file in Get-ChildItem -LiteralPath $dir -File) {
        if ($file.Name -eq 'process.json') { continue }
        $rel = $attempt+'\'+$file.Name
        $artifacts[$rel] = Hash $file.FullName
        Mirror $rel
    }
    $record['artifacts'] = $artifacts
    Save-Json (Join-Path $dir 'process.json') $record
    Mirror ($attempt+'\process.json')
    if ($failure) { throw $failure }
    $relative = 'records\'+$Case.id+'.json'
    Save-Json (Safe-Path $script:LocalRun $relative) $record
    Mirror $relative
    return [pscustomobject]$record
}
function Verify-Payload([string]$Root, $Manifest) {
    foreach ($file in $Manifest.files) {
        $p = Safe-Path $Root $file.path
        if (!(Test-Path -LiteralPath $p) -or (Hash $p) -ne $file.sha256) {
            throw "Missing or changed kit file: $p. Wait for complete Synology sync; do not skip this check."
        }
    }
}
function Write-Tables($Records) {
    $timing = @(); $accuracy = @()
    foreach ($r in $Records) {
        $c = $r.case
        if ($c.group -eq 'correctness') {
            $a = $r.accuracy
            $accuracy += [pscustomobject][ordered]@{case_id=$c.id; n=$c.n; distribution=$c.distribution; seed=$c.seed;
                solver=$c.solver; theta=$c.theta; threads=$c.threads; samples=$a.samples; rms_relative=$a.rms_relative;
                p95_particle_relative=$a.p95_particle_relative; max_particle_relative=$a.max_particle_relative}
        } else {
            $m = $r.metrics
            $timing += [pscustomobject][ordered]@{case_id=$c.id; group=$c.group; n=$c.n; distribution=$c.distribution;
                seed=$c.seed; repeat=$c.repeat; solver=$c.solver; threads=$c.threads;
                tree_ms=$m.tree_ms; kernel_ms=$m.kernel_ms; update_ms=$m.update_ms;
                force_update_ms=$m.force_update_ms; cleanup_ms=$m.cleanup_ms; total_ms=$m.total_ms}
        }
    }
    if ($timing.Count) {
        $timing | Export-Csv -LiteralPath (Join-Path $script:LocalRun 'timings.csv') -NoTypeInformation -Encoding UTF8
        Mirror 'timings.csv'
    }
    if ($accuracy.Count) {
        $accuracy | Export-Csv -LiteralPath (Join-Path $script:LocalRun 'accuracy.csv') -NoTypeInformation -Encoding UTF8
        Mirror 'accuracy.csv'
    }
}
function Run-Laptop {
    $KitRoot = [IO.Path]::GetFullPath($KitRoot)
    $script:HostRoot = Join-Path $KitRoot ('_wyniki\'+$env:COMPUTERNAME)
    $script:StopFile = Join-Path $script:HostRoot 'STOP.request'
    [IO.Directory]::CreateDirectory($script:HostRoot) | Out-Null
    if ($Mode -eq 'Stop') {
        Write-Atomic $script:StopFile ([DateTime]::UtcNow.ToString('o'))
        Write-Host 'Zlecono zatrzymanie. Wznowienie: 02_START_LUB_WZNOW.cmd.'
        return
    }
    if ($Mode -eq 'Status') {
        $statusKey = (Hash (Join-Path $KitRoot 'kit-manifest.json')).Substring(0,16)
        $statusRoot = Join-Path $LocalRoot ('runs\'+$statusKey)
        $localStatus = $null
        if (Test-Path -LiteralPath $statusRoot) {
            $localStatus = Get-ChildItem -LiteralPath $statusRoot -Filter status.json -Recurse -File |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
        }
        if ($localStatus) { Get-Content -LiteralPath $localStatus.FullName -Encoding UTF8 | Write-Host; return }
        $latest = Join-Path $script:HostRoot 'latest.json'
        if (Test-Path -LiteralPath $latest) { Get-Content -LiteralPath $latest -Encoding UTF8 | Write-Host }
        else { Write-Host 'Brak uruchomienia na tym komputerze.' }
        return
    }
    if (![Environment]::Is64BitProcess -or ![Environment]::Is64BitOperatingSystem) { throw 'Use 64-bit Windows PowerShell.' }
    [Threading.Thread]::CurrentThread.CurrentCulture = $script:Culture
    $manifestPath = Join-Path $KitRoot 'kit-manifest.json'
    $manifest = Read-Json $manifestPath
    $manifestHash = Hash $manifestPath
    $kitKey = $manifestHash.Substring(0,16)
    $script:LocalRun = Join-Path $LocalRoot ('runs\'+$kitKey+'\'+$Mode)
    $script:SyncRun = Join-Path $script:HostRoot ($kitKey+'-'+$Mode)
    [IO.Directory]::CreateDirectory($script:LocalRun) | Out-Null
    [IO.Directory]::CreateDirectory($script:SyncRun) | Out-Null
    # A local OS file lock, never a stale synced PID file. One launcher per laptop.
    try { $script:Lock = [IO.File]::Open((Join-Path $LocalRoot 'runner.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch { $script:LocalRun = $null; throw 'Another benchmark launcher is already running. Stop it before starting another.' }
    Restore-MirrorQueue
    if (Test-Path -LiteralPath $script:StopFile) { Remove-Item -LiteralPath $script:StopFile }
    Log "Runner=profile-guard-1; Mode=$Mode; kit=$kitKey; local=$script:LocalRun"
    Status 'preflight' 'Verifying kit hashes and laptop environment'
    Verify-Payload $KitRoot $manifest
    Add-Type -Path (Join-Path $KitRoot 'engine\runtime.cs')
    $cpu = @(Get-CimInstance Win32_Processor)
    $os = Get-CimInstance Win32_OperatingSystem
    $system = Get-CimInstance Win32_ComputerSystem
    $script:PowerScheme = Power-Scheme
    $powerDetails = Power-Details
    $script:PowerSettingsHash = Text-Hash $powerDetails
    $physical = ($cpu | Measure-Object NumberOfCores -Sum).Sum
    $logical = ($cpu | Measure-Object NumberOfLogicalProcessors -Sum).Sum
    $cpuName = ($cpu.Name -join '; ').Trim()
    if ([uint64]$system.TotalPhysicalMemory -lt 7GB) { throw 'At least 8 GB nominal RAM is required.' }
    foreach ($path in @($LocalRoot, $KitRoot)) {
        $drive = New-Object IO.DriveInfo([IO.Path]::GetPathRoot($path))
        if ($drive.AvailableFreeSpace -lt 2GB) { throw "Need 2 GB free on $($drive.Name)" }
    }
    $ignored = [ordered]@{}
    Get-ChildItem Env: | Where-Object Name -Match '^(OMP_|GOMP_|KMP_|RAYON_)' | Sort-Object Name | ForEach-Object { $ignored[$_.Name] = $_.Value }
    $identity = [ordered]@{host=$env:COMPUTERNAME; cpu=$cpuName; physical_cores=$physical; logical_cores=$logical;
        ram_bytes=[uint64]$system.TotalPhysicalMemory; windows_version=$os.Version; windows_build=$os.BuildNumber;
        power_scheme=$script:PowerScheme; power_settings_sha256=$script:PowerSettingsHash;
        affinity=[Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity.ToInt64();
        kit_manifest_sha256=$manifestHash; mode=$Mode; runtime_policy='OMP/GOMP/KMP/RAYON variables unset; bundled runtime DLLs'}
    $experiment = $null
    if ($manifest.PSObject.Properties.Name -contains 'experiment') {
        $experiment = $manifest.experiment
        $identity['requested_armoury_mode'] = $experiment.declared_armoury_mode
        $identity['experiment_label'] = $experiment.label
    }
    $script:Fingerprint = Text-Hash (Json $identity)
    $environment = [ordered]@{identity=$identity; fingerprint=$script:Fingerprint;
        captured_utc=[DateTime]::UtcNow.ToString('o'); powershell=$PSVersionTable.PSVersion.ToString();
        power_status=[LaptopRuntime]::Power(); ignored_parent_environment=$ignored;
        system_manufacturer=$system.Manufacturer; system_model=$system.Model;
        top_cpu_processes=@(Process-Snapshot)}
    Save-Json (Join-Path $script:LocalRun 'preflight-latest.json') $environment
    Mirror 'preflight-latest.json'
    Write-Atomic (Join-Path $script:LocalRun 'powercfg.txt') $powerDetails
    Mirror 'powercfg.txt'
    if ($Mode -eq 'Full' -and ($cpuName -notmatch 'i7-11370H' -or $physical -ne 4 -or $logical -ne 8 -or $identity.affinity -ne 255)) {
        throw "This profile expects i7-11370H, 4 cores / 8 threads and all CPUs enabled. Detected: $cpuName, $physical/$logical, affinity=$($identity.affinity). Send preflight logs; do not change the profile blindly."
    }
    Check-Power
    if ($null -ne $experiment) {
        Log ('Recorded Windows power scheme: ' + $script:PowerScheme)
        Check-ExperimentProfile $experiment $script:PowerScheme
        Write-Host 'Podlacz zasilacz, a NASTEPNIE wybierz Performance / Wydajnosc w Armoury Crate.' -ForegroundColor Yellow
        Write-Host 'Wylacz automatyczne przelaczanie profilu na czas pomiaru. Nie zmieniaj ustawien Windows w trakcie.'
        Write-Host 'Program nie odczytuje bezposrednio trybu Armoury Crate i nie zmienia ustawien komputera.'
        $answer = Read-Host 'Jesli wybrano Wydajnosc po podlaczeniu zasilacza, wpisz WYDAJNOSC'
        if ($answer.Trim() -cne 'WYDAJNOSC') { throw 'Profile not confirmed. No solver processes were started.' }
        Check-PowerConfiguration
        $environment['armoury_confirmation'] = [ordered]@{mode=$experiment.declared_armoury_mode;
            method='operator declaration, not an Armoury Crate sensor'; confirmed_utc=[DateTime]::UtcNow.ToString('o')}
        Save-Json (Join-Path $script:LocalRun 'preflight-latest.json') $environment
        Mirror 'preflight-latest.json'
    }
    $envPath = Join-Path $script:LocalRun 'environment.json'
    if (Test-Path -LiteralPath $envPath) {
        if ((Read-Json $envPath).fingerprint -ne $script:Fingerprint) { throw 'Hardware, OS, power scheme or affinity changed. Do not mix runs; retain logs and prepare a new campaign.' }
    } else { Save-Json $envPath $environment }
    Mirror 'environment.json'
    $payload = Join-Path $LocalRoot ('payload\'+$kitKey)
    Log 'Staging verified binaries and exact inputs on local disk (not in Synology).'
    foreach ($f in $manifest.files) {
        $target = Safe-Path $payload $f.path
        if (!(Test-Path -LiteralPath $target) -or (Hash $target) -ne $f.sha256) {
            [IO.Directory]::CreateDirectory((Split-Path -Parent $target)) | Out-Null
            [IO.File]::Copy((Safe-Path $KitRoot $f.path), $target, $true)
        }
    }
    Verify-Payload $payload $manifest
    $plan = Read-Json (Join-Path $payload 'plan.json')
    $cases = @($plan.$Mode)
    $script:Total = $cases.Count
    Copy-Item -LiteralPath (Join-Path $payload 'plan.json') -Destination (Join-Path $script:LocalRun 'plan.json')
    Mirror 'plan.json'
    $script:Job = [LaptopRuntime]::NewJob()
    [LaptopRuntime]::Awake($true)
    $records = New-Object 'Collections.Generic.List[object]'
    foreach ($case in $cases) {
        Flush-Mirrors
        $script:Current = $case.id
        if (Test-Path -LiteralPath $script:StopFile) { throw 'PAUSED: User requested stop.' }
        $record = Read-Success $case
        $newAttempt = $null -eq $record
        if ($null -eq $record) {
            Log ('[{0}/{1}] {2}' -f ($script:Done+1), $script:Total, $case.id)
            Status 'running'
            $record = Invoke-Case $case $payload
        } else {
            foreach ($artifact in $record.artifacts.PSObject.Properties) { Mirror $artifact.Name }
            Mirror ('records\'+$case.id+'.json')
        }
        $records.Add($record)
        $script:Done++
        Status 'running' 'Previous case saved and mirrored'
        # Brief idle interval for file sync; not part of the solver's measured time.
        if ($Mode -eq 'Full' -and $newAttempt) { Start-Sleep -Seconds 2 }
    }
    Write-Tables $records
    foreach ($case in $cases) { $null = Read-Success $case }
    Save-Json (Join-Path $script:LocalRun 'audit.json') ([ordered]@{passed=$true; mode=$Mode; records=$records.Count;
        expected=$cases.Count; environment_fingerprint=$script:Fingerprint; verified_utc=[DateTime]::UtcNow.ToString('o')})
    Mirror 'audit.json'
    $script:Current = ''
    Log "Local computation complete: $($script:Done) / $($script:Total). Checking mirror delivery."
    Flush-Mirrors -Limit 10000
    $completionState = 'complete'
    if ($script:PendingMirrors.Count) { $completionState = 'complete_sync_pending' }
    Status $completionState 'All planned cases succeeded and cached artifacts passed SHA-256 verification.'
    if ($script:PendingMirrors.Count) {
        Status 'complete_sync_pending' 'Results are safe locally. Rerun the same launcher to retry mirroring without repeating successful cases.'
        Write-Host "LOCAL COMPLETE: $($script:Done) / $($script:Total). SYNC PENDING: $($script:PendingMirrors.Count). Rerun the same launcher after files unlock. Local results: $script:LocalRun" -ForegroundColor Yellow
    } else {
        Write-Host "COMPLETE: $($script:Done) / $($script:Total). Results: $script:SyncRun"
    }
}

if (!$LibraryOnly) {
    $exitCode = 0
    try { Run-Laptop }
    catch {
        $exitCode = 2
        $message = ($_ | Format-List * -Force | Out-String) + "`r`n" + $_.ScriptStackTrace
        Write-Host $message -ForegroundColor Red
        if ($script:LocalRun) {
            try {
                Write-Atomic (Join-Path $script:LocalRun 'last-error.txt') $message
                Mirror 'last-error.txt'
                $state = 'failed'
                if ($_.Exception.Message -like '*PAUSED:*') { $state = 'paused'; $exitCode = 3 }
                Status $state $_.Exception.Message
            } catch { Write-Host "Could not mirror error; local results remain at $script:LocalRun" }
        }
    }
    finally {
        if ($script:Job -ne [IntPtr]::Zero) { [LaptopRuntime]::CloseJob($script:Job); [LaptopRuntime]::Awake($false) }
        if ($script:Lock) { $script:Lock.Dispose() }
    }
    exit $exitCode
}
