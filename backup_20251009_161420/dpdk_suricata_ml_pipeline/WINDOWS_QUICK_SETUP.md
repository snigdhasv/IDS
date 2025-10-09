# Windows Quick Setup Card

## 🚀 5-Minute Setup (NO INSTALLATION NEEDED!)

### 1. Configure Network (PowerShell as Admin)

```powershell
# Set static IP
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.100.2 -PrefixLength 24 -DefaultGateway 192.168.100.1

# Test
ping 192.168.100.1
```

### 2. Generate Traffic (Choose ONE method)

#### ⭐ Option A: PowerShell Only (RECOMMENDED - No Install!)

```powershell
# HTTP flood
1..100 | ForEach-Object { 
    curl "http://192.168.100.1" 
    Write-Host "Request $_"
}

# Port scan
1..1000 | ForEach-Object {
    Test-NetConnection -ComputerName 192.168.100.1 -Port $_ -WarningAction SilentlyContinue
}
```

#### Option B: With Python/Scapy

```powershell
# Install
pip install scapy

# Run
python -c "from scapy.all import *; sendp([IP(dst='192.168.100.1')/TCP(dport=80, flags='S')]*100, iface='Ethernet')"
```

#### Option C: With tcpreplay

```powershell
# Download from: https://github.com/appneta/tcpreplay/releases
tcpreplay -i "Ethernet" --mbps=10 attack.pcap
```

---

## 📋 Complete PowerShell Scripts

### All-in-One Attack Script

```powershell
# Save as: attack_simulator.ps1
$target = "192.168.100.1"

Write-Host "Starting attack simulation..." -ForegroundColor Cyan

# 1. Port scan
Write-Host "[1/3] Port scanning..." -ForegroundColor Yellow
1..100 | ForEach-Object {
    Test-NetConnection -ComputerName $target -Port $_ -WarningAction SilentlyContinue | Out-Null
}

# 2. HTTP flood
Write-Host "[2/3] HTTP requests..." -ForegroundColor Yellow
1..50 | ForEach-Object {
    try { Invoke-WebRequest -Uri "http://$target" -TimeoutSec 1 } catch {}
}

# 3. SQL injection
Write-Host "[3/3] SQL injection attempts..." -ForegroundColor Yellow
@("' OR '1'='1", "admin'--") | ForEach-Object {
    try { Invoke-WebRequest -Uri "http://$target/login?user=$_" -TimeoutSec 1 } catch {}
}

Write-Host "Complete!" -ForegroundColor Green
```

**Run it:**

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\attack_simulator.ps1
```

---

## 🐛 Troubleshooting

### Can't ping IDS?

```powershell
# Check cable
Get-NetAdapter | Where-Object {$_.Name -eq "Ethernet"} | Select Status

# Check IP
Get-NetIPAddress -InterfaceAlias "Ethernet" -AddressFamily IPv4

# Disable firewall temporarily
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
ping 192.168.100.1
# Re-enable
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

### Wrong interface name?

```powershell
# List all adapters
Get-NetAdapter | Format-Table Name, Status

# Use correct name in commands
$AdapterName = "Ethernet 2"  # or whatever yours is called
New-NetIPAddress -InterfaceAlias $AdapterName -IPAddress 192.168.100.2 -PrefixLength 24
```

---

## 📚 Full Documentation

See **`WINDOWS_EXTERNAL_DEVICE_GUIDE.md`** for:
- ✅ Detailed setup instructions
- ✅ Multiple traffic generation methods
- ✅ Python/Scapy examples
- ✅ tcpreplay installation
- ✅ Attack simulation scripts
- ✅ Advanced troubleshooting

See **`WINDOWS_NO_TCPREPLAY.md`** for:
- ✅ PowerShell-only traffic generation (no install!)
- ✅ 10+ ready-to-use attack scripts
- ✅ Python/Scapy alternatives to tcpreplay
- ✅ PCAP replay without tcpreplay

---

## 🎯 Summary

| Item | Value |
|------|-------|
| Windows IP | 192.168.100.2 |
| IDS IP | 192.168.100.1 |
| Interface | "Ethernet" |
| Easiest Method | PowerShell (built-in!) |
| Best Tool | tcpreplay or Scapy |

**That's it! Start generating traffic and watch your IDS detect attacks! 🚀**
