# METROREC — Sistema de Mobilidade Integrado

Aplicativo demonstrativo de mobilidade feito em Python e Tkinter.

## Executar no Windows

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Gerar o executável

Instale as dependências de build e rode o empacotador. O PowerShell pode exigir `ExecutionPolicy Bypass` para executar o script:

```powershell
python -m pip install -r requirements-build.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

O executável será criado em `dist/MetroREC.exe`. A imagem `assets/metrorec-logo.png` é usada no ícone da janela, e `assets/metrorec-logo.ico` no `.exe`. As configurações operacionais do aplicativo empacotado são armazenadas em `%LOCALAPPDATA%\MetroREC\operacao.json`.

## Recursos

Os cards das linhas usam `assets/linha-jaboatao.png`, `assets/linha-camaragibe.png` e `assets/linha-sul.png`. O cabeçalho usa `assets/cabecalho-trem.png` e a marca CBTU usa `assets/logo-cbtu.png`.

O painel administrativo permite ajustar tarifa, estado e intervalo de referência das linhas, cadastrar maquinistas, designá-los aos trens, controlar a frota e registrar ou resolver ocorrências. Os dados são locais e não são enviados à CBTU. O planejamento bloqueia linhas indisponíveis e considera a espera estimada pelo intervalo.

O mapa usa `tkintermapview` e serviços GIS online. A simulação e a administração são demonstrativas; não se conectam a despacho, bilhetagem, folha funcional ou sistemas operacionais reais. Tarifas, velocidades, intervalos e tempos são parâmetros acadêmicos, não dados oficiais.
