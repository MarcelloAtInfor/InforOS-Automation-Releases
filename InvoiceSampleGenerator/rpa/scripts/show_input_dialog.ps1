param(
    [Parameter(Mandatory = $true)][string]$RequestJsonPath,
    [Parameter(Mandatory = $true)][string]$OutputRequestJsonPath
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# ── Load defaults from request JSON ──────────────────────────────
$defaults = @{}
if (Test-Path $RequestJsonPath) {
    $defaults = Get-Content -Raw -Path $RequestJsonPath -Encoding UTF8 | ConvertFrom-Json
}
function Val([string]$key, [string]$fallback) {
    $v = $defaults.$key
    if ($null -ne $v -and $v.ToString().Trim().Length -gt 0) { return $v.ToString().Trim() }
    return $fallback
}

# ── Build form ───────────────────────────────────────────────────
$form = New-Object System.Windows.Forms.Form
$form.Text = "Invoice Sample Generator"
$form.StartPosition = "CenterScreen"
$form.AutoSize = $true
$form.AutoSizeMode = "GrowAndShrink"
$form.MinimumSize = New-Object System.Drawing.Size(480, 300)
$form.MaximizeBox = $false
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

$y = 15
function AddLabel([string]$text) {
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = $text
    $lbl.Location = New-Object System.Drawing.Point(15, $script:y)
    $lbl.AutoSize = $true
    $form.Controls.Add($lbl)
    $script:y += 20
}
function AddTextBox([string]$default, [int]$width = 420, [string]$placeholder = "") {
    $tb = New-Object System.Windows.Forms.TextBox
    $tb.Location = New-Object System.Drawing.Point(15, $script:y)
    $tb.Size = New-Object System.Drawing.Size($width, 23)
    
    if ($placeholder -ne "" -and $default -eq "") {
        $tb.Text = $placeholder
        $tb.ForeColor = [System.Drawing.Color]::Gray
        $tb.Add_GotFocus({
            if ($this.ForeColor -eq [System.Drawing.Color]::Gray) {
                $this.Text = ""
                $this.ForeColor = [System.Drawing.Color]::Black
            }
        })
        $tb.Add_LostFocus({
            if ($this.Text -eq "") {
                $this.Text = $this.Tag
                $this.ForeColor = [System.Drawing.Color]::Gray
            }
        })
        $tb.Tag = $placeholder
    } else {
        $tb.Text = $default
    }
    
    $form.Controls.Add($tb)
    $script:y += 30
    return $tb
}
function AddCombo([string[]]$items, [string]$default) {
    $cb = New-Object System.Windows.Forms.ComboBox
    $cb.DropDownStyle = "DropDownList"
    $cb.Location = New-Object System.Drawing.Point(15, $script:y)
    $cb.Size = New-Object System.Drawing.Size(200, 23)
    $cb.Items.AddRange($items)
    $idx = [Array]::IndexOf($items, $default)
    $cb.SelectedIndex = if ($idx -ge 0) { $idx } else { 0 }
    $form.Controls.Add($cb)
    $script:y += 30
    return $cb
}
function AddCheck([string]$text, [bool]$default) {
    $chk = New-Object System.Windows.Forms.CheckBox
    $chk.Text = $text
    $chk.Checked = $default
    $chk.Location = New-Object System.Drawing.Point(15, $script:y)
    $chk.AutoSize = $true
    $form.Controls.Add($chk)
    $script:y += 28
    return $chk
}

# ── Controls ─────────────────────────────────────────────────────
AddLabel "Document Count"
$tbCount = AddTextBox (Val "documentCount" "3")

AddLabel "Document Mode"
$cbMode = AddCombo @("PO", "Non-PO") $(if ((Val "isNonPo" "False") -eq "True") { "Non-PO" } else { "PO" })

AddLabel "Lines Per Invoice (e.g. 4 or 2-6 for range)"
$tbLines = AddTextBox (Val "lineCount" "4")

AddLabel "Quantity Per Line (e.g. 5 or 1-10 for range)"
$tbQty = AddTextBox (Val "qtyRange" "1-10")

AddLabel "Output Folder"
$tbOutput = AddTextBox (Val "outputFolder" "C:\InforRPA\InvoiceSampleGenerator\Output\GeneratedBatch")

AddLabel "Invoice Date (YYYY-MM-DD)"
$tbDate = AddTextBox (Get-Date -Format "yyyy-MM-dd")

AddLabel "Tax Percent"
$tbTax = AddTextBox (Val "taxPercent" "8.00")

AddLabel "Invoice Prefix"
$tbInvPrefix = AddTextBox (Val "invoicePrefix" "INVDM") 100

AddLabel "PO Prefix"
$tbPoPrefix = AddTextBox (Val "poPrefix" "PODM") 100

$chkCSI = AddCheck "Use live CSI vendors and items" $true
$chkReuseVendor = AddCheck "Reuse same vendor across batch" $false

AddLabel "Selected Vendors (pipe-delimited, blank = random from CSI)"
$tbVendors = AddTextBox "" 420 "e.g. VEND001|VEND002"

AddLabel "Selected Items (pipe-delimited, blank = random from CSI)"
$tbItems = AddTextBox "" 420 "e.g. ITEM001|ITEM002|ITEM003"

$chkLookupNumbers = AddCheck "Lookup latest PO/invoice numbers from CSI" $true
$chkPaired = AddCheck "Pair invoice and PO number sequences" $((Val "pairInvoiceAndPoSequence" "True") -eq "True")

$y += 10

# ── Buttons ──────────────────────────────────────────────────────
$y += 10
$btnOK = New-Object System.Windows.Forms.Button
$btnOK.Text = "Generate"
$btnOK.Size = New-Object System.Drawing.Size(100, 32)
$btnOK.Location = New-Object System.Drawing.Point(250, $y)
$btnOK.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $btnOK
$form.Controls.Add($btnOK)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "Cancel"
$btnCancel.Size = New-Object System.Drawing.Size(100, 32)
$btnCancel.Location = New-Object System.Drawing.Point(360, $y)
$btnCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.CancelButton = $btnCancel
$form.Controls.Add($btnCancel)

# Spacer for auto-size
$spacer = New-Object System.Windows.Forms.Label
$spacer.Location = New-Object System.Drawing.Point(0, ($y + 45))
$spacer.Size = New-Object System.Drawing.Size(470, 1)
$form.Controls.Add($spacer)

# ── Show ─────────────────────────────────────────────────────────
$result = $form.ShowDialog()
if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
    Write-Host "CANCELLED"
    exit 1
}

# ── Build request from form values ───────────────────────────────
function GetTextValue($tb) {
    if ($tb.ForeColor -eq [System.Drawing.Color]::Gray) { return "" }
    return $tb.Text.Trim()
}

$isNonPo = ($cbMode.SelectedItem -eq "Non-PO")
$useCSI = $chkCSI.Checked

$request = [ordered]@{
    documentCount              = $tbCount.Text.Trim()
    isNonPo                    = $(if ($isNonPo) { "True" } else { "False" })
    layoutVariant              = "html_reference_v1"
    outputFolder               = $tbOutput.Text.Trim()
    randomSeed                 = (Get-Date -Format "yyyyMMdd")
    useExistingVendors         = $(if ($useCSI) { "True" } else { "False" })
    selectedVendor             = GetTextValue $tbVendors
    reuseSameVendorAcrossBatch = $(if ($chkReuseVendor.Checked) { "True" } else { "False" })
    useExistingItems           = $(if ($useCSI) { "True" } else { "False" })
    selectedItems              = GetTextValue $tbItems
    lineCount                  = $tbLines.Text.Trim()
    qtyRange                   = $tbQty.Text.Trim()
    dateMode                   = "fixed"
    fixedInvoiceDate           = $(if ($tbDate.Text.Trim().Length -gt 0) { $tbDate.Text.Trim() } else { (Get-Date -Format "yyyy-MM-dd") })
    futureDateAllowed          = "True"
    lookupLatestNumbers        = $(if ($chkLookupNumbers.Checked) { "True" } else { "False" })
    pairInvoiceAndPoSequence   = $(if ($chkPaired.Checked) { "True" } else { "False" })
    invoiceStartValue          = Val "invoiceStartValue" ""
    poStartValue               = Val "poStartValue" ""
    invoicePrefix              = $tbInvPrefix.Text.Trim()
    invoiceStartNumber         = Val "invoiceStartNumber" ""
    invoiceWidth               = Val "invoiceWidth" "3"
    poPrefix                   = $tbPoPrefix.Text.Trim()
    poStartNumber              = Val "poStartNumber" ""
    poWidth                    = Val "poWidth" "6"
    taxMode                    = "percent_of_subtotal"
    taxPercent                 = $tbTax.Text.Trim()
    fixedTaxAmount             = ""
    writeManifest              = "True"
    writePerInvoiceJson        = "True"
    fileNamePattern            = "{invoice_number}_{mode}.pdf"
}

# ── Write ────────────────────────────────────────────────────────
$outDir = Split-Path -Parent $OutputRequestJsonPath
if (-not [string]::IsNullOrWhiteSpace($outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$request | ConvertTo-Json -Depth 5 -Compress | Set-Content -Path $OutputRequestJsonPath -Encoding UTF8
Write-Host "OK"
Write-Host $OutputRequestJsonPath
