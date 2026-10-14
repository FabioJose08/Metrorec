$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$logo = Join-Path $project 'assets\metrorec-logo.png'
$imagemOrigem = Join-Path $project 'assets\logo.ico'
$icon = Join-Path $project 'assets\metrorec-logo.ico'

if (-not (Test-Path -LiteralPath $logo) -and (Test-Path -LiteralPath $imagemOrigem)) {
    python -c "from PIL import Image; Image.open(r'$imagemOrigem').convert('RGBA').save(r'$logo')"
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível converter a imagem de origem.' }
}
if (-not (Test-Path -LiteralPath $logo)) {
    throw "Logo não encontrada. Salve a imagem em assets\metrorec-logo.png ou assets\logo.ico."
}

python -c "from PIL import Image; im=Image.open(r'$logo').convert('RGBA'); im.save(r'$icon', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível converter a logo para ICO.' }

Push-Location $project
try {
    python -m PyInstaller --noconfirm --clean --onefile --windowed --name MetroREC `
        --icon $icon --add-data 'assets;assets' --add-data 'operacao.json;.' `
        --collect-all tkintermapview main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller falhou.' }
} finally {
    Pop-Location
}
Write-Host "Executável criado em: $(Join-Path $project 'dist\MetroREC.exe')"
