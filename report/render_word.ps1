param([Parameter(Mandatory=$true)][string]$InputDocx,[Parameter(Mandatory=$true)][string]$OutputPdf,[switch]$Update)
$ErrorActionPreference='Stop'
$sourcePath=(Resolve-Path -LiteralPath $InputDocx).Path
$pdfPath=[IO.Path]::GetFullPath($OutputPdf)
$word=$null
$doc=$null
try {
  $word=New-Object -ComObject Word.Application
  $word.Visible=$false
  $word.DisplayAlerts=0
  $doc=$word.Documents.Open($sourcePath,$false,(-not $Update.IsPresent))
  if ($Update) {
    $null=$doc.Fields.Update()
    foreach ($toc in $doc.TablesOfContents) {$null=$toc.Update()}
    $doc.Repaginate()
    $null=$doc.Fields.Update()
    $doc.Save()
  }
  $doc.ExportAsFixedFormat($pdfPath,17)
  Write-Output ('PDF: '+$pdfPath)
  Write-Output ('Pages: '+$doc.ComputeStatistics(2))
} finally {
  if ($doc) {$doc.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)}
  if ($word) {$word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
