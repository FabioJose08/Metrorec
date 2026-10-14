$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$assets = Join-Path $project 'assets'
$logo = Join-Path $assets 'metrorec-logo.png'
$sourceLogo = Join-Path $assets 'logo.ico'
$icon = Join-Path $assets 'metrorec-logo.ico'
$hooks = Join-Path $project 'pyinstaller_hooks'
$pythonRoot = (python -c "import sys; print(sys.base_prefix)").Trim()
$tcl = Join-Path $pythonRoot 'tcl\tcl8.6'
$tk = Join-Path $pythonRoot 'tcl\tk8.6'

if (-not (Test-Path -LiteralPath $logo) -and (Test-Path -LiteralPath $sourceLogo)) {
    python -c "from PIL import Image; Image.open(r'$sourceLogo').convert('RGBA').save(r'$logo')"
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível converter a imagem de origem.' }
}
if (-not (Test-Path -LiteralPath $logo)) { throw 'Logo ausente em assets\metrorec-logo.png.' }
if (-not (Test-Path -LiteralPath (Join-Path $tcl 'init.tcl')) -or -not (Test-Path -LiteralPath (Join-Path $tk 'tk.tcl'))) {
    throw "Runtime Tcl/Tk não encontrado na instalação Python: $pythonRoot. Instale o Python completo com Tcl/Tk."
}

python -c "from PIL import Image; Image.open(r'$logo').convert('RGBA').save(r'$icon', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível converter a logo para ICO.' }

Push-Location $project
try {
    python -m PyInstaller --noconfirm --clean --onefile --windowed --name MetroREC `
        --icon $icon --additional-hooks-dir $hooks `
        --add-data 'assets;assets' --add-data 'operacao.json;.' `
        --add-data "$tcl;_tcl_data" --add-data "$tk;_tk_data" `
        --add-binary "$pythonRoot\DLLs\tcl86t.dll;." --add-binary "$pythonRoot\DLLs\tk86t.dll;." `
        --hidden-import tkinter --hidden-import _tkinter `
        --collect-all tkintermapview main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller falhou.' }
} finally { Pop-Location }
Write-Host "Executável criado em: $(Join-Path $project 'dist\MetroREC.exe')"
