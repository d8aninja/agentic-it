<#
.SYNOPSIS
    Wi-Fi remediation script for Windows.
    Called by actions/network_actions.py with one argument:
        reconnect        — disconnect and reconnect to the current known network
        restart          — disable and re-enable the Wi-Fi adapter
        forget_and_rejoin — forget the saved profile and reconnect (prompts if SSID not known)
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("reconnect", "restart", "forget_and_rejoin")]
    [string]$Action
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-WifiAdapterName {
    $adapter = Get-NetAdapter | Where-Object { $_.PhysicalMediaType -eq "Native 802.11" -and $_.Status -eq "Up" } | Select-Object -First 1
    if (-not $adapter) {
        $adapter = Get-NetAdapter | Where-Object { $_.Name -like "*Wi-Fi*" -or $_.Name -like "*Wireless*" } | Select-Object -First 1
    }
    if (-not $adapter) { throw "No active Wi-Fi adapter found." }
    return $adapter.Name
}

function Get-CurrentSSID {
    $profile = netsh wlan show interfaces | Select-String "^\s+SSID\s+:" | Select-Object -First 1
    if ($profile) {
        return ($profile -split ":\s+", 2)[1].Trim()
    }
    return $null
}

switch ($Action) {
    "reconnect" {
        $ssid = Get-CurrentSSID
        if (-not $ssid) { throw "Not connected to any Wi-Fi network." }
        Write-Output "Disconnecting from '$ssid'..."
        netsh wlan disconnect | Out-Null
        Start-Sleep -Seconds 2
        Write-Output "Reconnecting to '$ssid'..."
        netsh wlan connect name="$ssid" | Out-Null
        Start-Sleep -Seconds 3
        Write-Output "Reconnect to '$ssid' issued successfully."
    }

    "restart" {
        $adapterName = Get-WifiAdapterName
        Write-Output "Disabling adapter '$adapterName'..."
        Disable-NetAdapter -Name $adapterName -Confirm:$false
        Start-Sleep -Seconds 3
        Write-Output "Re-enabling adapter '$adapterName'..."
        Enable-NetAdapter -Name $adapterName -Confirm:$false
        Start-Sleep -Seconds 5
        Write-Output "Adapter '$adapterName' restarted."
    }

    "forget_and_rejoin" {
        $ssid = Get-CurrentSSID
        if (-not $ssid) { throw "Not connected to any Wi-Fi network - cannot forget and rejoin." }

        # Back up credentials before touching the profile; abort if none are saved.
        $tempDir = Join-Path $env:TEMP "wifi_backup_$(Get-Date -Format 'yyyyMMddHHmmss')"
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        try {
            netsh wlan export profile name="$ssid" folder="$tempDir" key=clear | Out-Null
            $exportedFile = Get-ChildItem -Path $tempDir -Filter "*.xml" | Select-Object -First 1
            if (-not $exportedFile) {
                throw "No saved credentials found for '$ssid'. Aborting forget_and_rejoin to avoid leaving device disconnected."
            }
            Write-Output "Credentials backed up."

            Write-Output "Forgetting profile '$ssid'..."
            netsh wlan disconnect | Out-Null
            netsh wlan delete profile name="$ssid" | Out-Null
            Start-Sleep -Seconds 2

            Write-Output "Reconnecting to '$ssid'..."
            netsh wlan connect name="$ssid" | Out-Null
            Start-Sleep -Seconds 5

            if ((Get-CurrentSSID) -eq $ssid) {
                Write-Output "Successfully reconnected to '$ssid'."
            } else {
                Write-Output "Reconnect failed - restoring saved profile..."
                netsh wlan add profile filename="$($exportedFile.FullName)" | Out-Null
                throw "Could not reconnect to '$ssid' after profile deletion. Saved profile restored; credentials preserved."
            }
        } finally {
            Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
        }
    }
}
