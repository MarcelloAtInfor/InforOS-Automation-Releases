param(
    [Parameter(Mandatory = $true)][string]$RequestJsonPath,
    [string]$VendorResponseJsonPath = "",
    [string]$ItemResponseJsonPath = "",
    [string]$PoNumberResponseJsonPath = "",
    [Parameter(Mandatory = $true)][string]$EnrichedRequestJsonPath
)

$ErrorActionPreference = "Stop"

# ── Read original request ────────────────────────────────────────
$request = Get-Content -Raw -Path $RequestJsonPath -Encoding UTF8 | ConvertFrom-Json

# ── Helper: extract Items array from IDO response ───────────────
function Get-IdoItems([string]$jsonPath) {
    if ([string]::IsNullOrWhiteSpace($jsonPath) -or -not (Test-Path $jsonPath)) { return ,@() }
    $text = Get-Content -Raw -Path $jsonPath -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($text)) { return ,@() }
    if ($text.Contains('"error"')) { return ,@() }
    $data = $text | ConvertFrom-Json
    if ($data -is [array]) { return ,$data }
    if ($null -ne $data.Items) { return ,@($data.Items) }
    return ,@()
}

$warnings = @()

# ── Vendor resolution ────────────────────────────────────────────
$useVendors = ($request.useExistingVendors -eq "True")
$selectedVendor = if ($null -ne $request.selectedVendor) { $request.selectedVendor.Trim() } else { "" }

if ($useVendors -and -not [string]::IsNullOrWhiteSpace($VendorResponseJsonPath)) {
    $vendors = Get-IdoItems $VendorResponseJsonPath
    if ($vendors.Count -gt 0) {
        # Build csiVendors array from IDO response
        $csiVendors = @()
        foreach ($v in $vendors) {
            $vc = ($v.VendNum).ToString().Trim()
            $addrLines = @()
            foreach ($f in @("VadAddr_1","VadAddr_2","VadAddr_3","VadAddr_4")) {
                $val = if ($null -ne $v.$f) { $v.$f.ToString().Trim() } else { "" }
                if ($val.Length -gt 0) { $addrLines += $val }
            }
            $city = if ($null -ne $v.VadCity) { $v.VadCity.ToString().Trim() } else { "" }
            $state = if ($null -ne $v.VadState) { $v.VadState.ToString().Trim() } else { "" }
            $zip = if ($null -ne $v.VadZip) { $v.VadZip.ToString().Trim() } else { "" }
            $csz = (@($city, $state) | Where-Object { $_.Length -gt 0 }) -join ", "
            if ($zip.Length -gt 0) { $csz = "$csz $zip" }
            if ($csz.Trim().Length -gt 0) { $addrLines += $csz.Trim() }
            $csiVendors += [PSCustomObject]@{
                code = $vc
                name = if ($null -ne $v.Name) { $v.Name.ToString().Trim() } else { $vc }
                address_lines = $addrLines
                phone = if ($null -ne $v.Phone) { $v.Phone.ToString().Trim() } else { "" }
                email = if ($null -ne $v.ExternalEmailAddr) { $v.ExternalEmailAddr.ToString().Trim() } else { "" }
            }
        }
        if ($csiVendors.Count -gt 0) {
            $request | Add-Member -NotePropertyName "csiVendors" -NotePropertyValue $csiVendors -Force
            $warnings += "CSI: Loaded $($csiVendors.Count) vendor details."
        }
    } else {
        $warnings += "CSI: Vendor lookup returned no results; falling back to local catalog."
    }
}

# ── Item resolution ──────────────────────────────────────────────
$useItems = ($request.useExistingItems -eq "True")

if ($useItems -and -not [string]::IsNullOrWhiteSpace($ItemResponseJsonPath)) {
    $items = Get-IdoItems $ItemResponseJsonPath
    if ($items.Count -gt 0) {
        # Build csiItems array from IDO response
        $csiItems = @()
        foreach ($it in $items) {
            $ic = ($it.Item).ToString().Trim()
            $unitCost = "0.00"
            if ($null -ne $it.UnitCost) {
                try { $unitCost = [decimal]::Parse($it.UnitCost.ToString()).ToString("F2") } catch { $unitCost = "0.00" }
            }
            $csiItems += [PSCustomObject]@{
                code = $ic
                description = if ($null -ne $it.Description) { $it.Description.ToString().Trim() } else { $ic }
                uom = if ($null -ne $it.UM) { $it.UM.ToString().Trim() } else { "EA" }
                unit_price = $unitCost
            }
        }
        if ($csiItems.Count -gt 0) {
            $request | Add-Member -NotePropertyName "csiItems" -NotePropertyValue $csiItems -Force
            $warnings += "CSI: Loaded $($csiItems.Count) item details."
        }
    } else {
        $warnings += "CSI: Item lookup returned no results; falling back to local catalog."
    }
}

# ── PO numbering resolution ─────────────────────────────────────
$lookupNumbers = ($request.lookupLatestNumbers -eq "True")
$isNonPo = ($request.isNonPo -eq "True")

if ($lookupNumbers -and -not $isNonPo -and -not [string]::IsNullOrWhiteSpace($PoNumberResponseJsonPath)) {
    $poRows = Get-IdoItems $PoNumberResponseJsonPath
    if ($poRows.Count -gt 0) {
        $poNum = ($poRows[0].PoNum).ToString().Trim()
        # Extract trailing digits
        $digits = ""
        for ($i = $poNum.Length - 1; $i -ge 0; $i--) {
            if ($poNum[$i] -match '\d') { $digits = $poNum[$i] + $digits } else { break }
        }
        if ($digits.Length -gt 0) {
            $nextNum = [int]$digits + 1
            $poPrefix = if ($null -ne $request.poPrefix -and $request.poPrefix.Trim().Length -gt 0) { $request.poPrefix.Trim() } else { "PODM" }
            $poWidth = if ($null -ne $request.poWidth -and [int]$request.poWidth -gt 0) { [int]$request.poWidth } else { 6 }
            $request.poStartValue = $poPrefix + $nextNum.ToString().PadLeft($poWidth, '0')

            # If paired, also set invoice start
            if ($request.pairInvoiceAndPoSequence -eq "True") {
                $invPrefix = if ($null -ne $request.invoicePrefix -and $request.invoicePrefix.Trim().Length -gt 0) { $request.invoicePrefix.Trim() } else { "INVDM" }
                $invWidth = if ($null -ne $request.invoiceWidth -and [int]$request.invoiceWidth -gt 0) { [int]$request.invoiceWidth } else { 3 }
                $request.invoiceStartValue = $invPrefix + $nextNum.ToString().PadLeft($invWidth, '0')
            }
            $warnings += "CSI: Resolved next PO number from latest $poNum -> $($request.poStartValue)"
        }
    } else {
        $warnings += "CSI: PO number lookup returned no results; falling back to configured defaults."
    }
}

# ── Write enriched request ───────────────────────────────────────
$enrichedDir = Split-Path -Parent $EnrichedRequestJsonPath
if (-not [string]::IsNullOrWhiteSpace($enrichedDir)) {
    New-Item -ItemType Directory -Path $enrichedDir -Force | Out-Null
}
$request | ConvertTo-Json -Depth 10 | Set-Content -Path $EnrichedRequestJsonPath -Encoding UTF8

# ── Output summary ───────────────────────────────────────────────
foreach ($w in $warnings) { Write-Host $w }
if ($warnings.Count -eq 0) { Write-Host "CSI: No enrichment needed or no data available." }
Write-Host "Enriched request written to: $EnrichedRequestJsonPath"
