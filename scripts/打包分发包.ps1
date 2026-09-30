# ============================================================
# dp-jf 分发包打包脚本
# 用途：生成发给别人的安装包 zip（剔除体积大头与本机私有数据）
# 用法：powershell -ExecutionPolicy Bypass -File scripts/打包分发包.ps1
# 产物：技能文件夹同级 dp-jf_v{版本}_安装包.zip
# 排除：知识卡片库/PNG截图（24MB，走云盘单独发）、CHANGELOG.md（历史日志）、
#       __pycache__、*.bak/*.pyc、config/设置.md（本机私有）、学员数据
# ============================================================
$ErrorActionPreference = 'Stop'

$skillRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$versionMatch = Select-String -Path (Join-Path $skillRoot 'version.md') -Pattern '当前版本：\s*(.+)'
$version = $versionMatch.Matches[0].Groups[1].Value.Trim().TrimStart("v")
$distZip = Join-Path (Split-Path $skillRoot -Parent) "dp-jf_v${version}_安装包.zip"
$stage = Join-Path $skillRoot '_打包临时'

function Assert-InsideSkillRoot {
    param([string]$Path)
    $resolved = (Resolve-Path $Path).Path
    if (-not $resolved.StartsWith($skillRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "路径越界，拒绝操作：$resolved"
    }
    return $resolved
}

# 清理旧暂存目录（先校验路径在技能目录内）
if (Test-Path $stage) {
    $resolvedStage = Assert-InsideSkillRoot $stage
    Remove-Item -LiteralPath $resolvedStage -Recurse -Force
}
New-Item -ItemType Directory -Path $stage | Out-Null
$stageInner = Join-Path $stage 'dp-jf'
New-Item -ItemType Directory -Path $stageInner | Out-Null

# 排除规则
$excludeDirNames = @('__pycache__', 'PNG截图', '_打包临时', '学员', '.git')
$excludeFileNames = @('CHANGELOG.md', '设置.md')
$excludeExtensions = @('.bak', '.pyc')

Get-ChildItem -LiteralPath $skillRoot -Recurse -File | Where-Object {
    $file = $_
    $relDirs = @()
    if ($file.DirectoryName.Length -gt $skillRoot.Length) {
        $relDirs = $file.DirectoryName.Substring($skillRoot.Length).TrimStart('\') -split '\\'
    }
    $inExcludedDir = $false
    foreach ($dir in $relDirs) { if ($excludeDirNames -contains $dir) { $inExcludedDir = $true; break } }
    (-not $inExcludedDir) -and
    ($excludeFileNames -notcontains $file.Name) -and
    ($excludeExtensions -notcontains $file.Extension)
} | ForEach-Object {
    $rel = $_.DirectoryName.Substring($skillRoot.Length).TrimStart('\')
    $destDir = if ($rel) { Join-Path $stageInner $rel } else { $stageInner }
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $destDir $_.Name)
}

if (Test-Path $distZip) { Remove-Item -LiteralPath $distZip -Force }
Compress-Archive -Path $stageInner -DestinationPath $distZip -Force

# 清理暂存目录（再次校验路径）
$resolvedStage = Assert-InsideSkillRoot $stage
Remove-Item -LiteralPath $resolvedStage -Recurse -Force

$size = [math]::Round((Get-Item $distZip).Length / 1MB, 2)
$fileCount = (Get-ChildItem $skillRoot -Recurse -File | Where-Object {
    $rel = $_.DirectoryName.Substring($skillRoot.Length)
    $rel -notmatch '(__pycache__|PNG截图|_打包临时|\\学员\\|\.git)' -and $_.Name -ne 'CHANGELOG.md' -and $_.Name -ne '设置.md' -and $_.Extension -ne '.bak' -and $_.Extension -ne '.pyc'
}).Count
Write-Output "打包完成：$distZip"
Write-Output "体积：${size} MB｜文件数：$fileCount"
Write-Output "已排除：PNG截图（走云盘单独发）、CHANGELOG、__pycache__、本机设置、学员数据"