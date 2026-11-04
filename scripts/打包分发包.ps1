param([string]$OutputPath = "")
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot '打包分发包.py'
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    & python $script
} else {
    & python $script --output $OutputPath
}
exit $LASTEXITCODE
