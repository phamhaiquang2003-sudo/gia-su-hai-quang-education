$url = $null
$tunnels = Get-Process cloudflared -ErrorAction SilentlyContinue

foreach ($tunnel in $tunnels) {
    $listeners = Get-NetTCPConnection -OwningProcess $tunnel.Id -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -eq '127.0.0.1' }
    foreach ($listener in $listeners) {
        try {
            $metrics = (Invoke-WebRequest "http://127.0.0.1:$($listener.LocalPort)/metrics" -UseBasicParsing -TimeoutSec 3).Content
            if ($metrics -match 'userHostname="(https://[a-z0-9-]+\.trycloudflare\.com)"') {
                $url = $Matches[1]
                break
            }
        } catch {
            # A different local listener may not expose Cloudflare metrics.
        }
    }
    if ($url) { break }
}

if ($url) {
    Write-Host "Link hoc sinh: $url" -ForegroundColor Green
    try {
        Set-Clipboard -Value $url
        Write-Host 'Da sao chep link vao bo nho tam. Co the dan truc tiep vao tin nhan.'
    } catch {
        Write-Host 'Khong tu dong sao chep duoc; hay chon link o dong tren de sao chep.'
    }
} else {
    Write-Host 'Chua tim thay link. Hay mo chay-website.bat va chay-tu-xa.bat truoc.' -ForegroundColor Yellow
    exit 1
}
