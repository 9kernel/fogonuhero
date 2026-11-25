# FogonuHero

Jogo de percussão de carnaval em Godot, com interface em português brasileiro. A demonstração **Cortejo de Neon** acompanha dois exercícios originais de caixa de guerra. Use **F** e **J** ou as duas áreas de toque. Pressione **Esc** ou toque no topo da partida para pausar.

## Executar e testar

Instale o **Godot 4.5.1 stable**, seus templates de exportação da mesma versão e Python 3.10 ou 3.11. Adicione o executável do Godot ao PATH com o nome `godot`. A exportação usa WebGL 2, Compatibility e single-thread.

```sh
godot --path game
python3 -m unittest discover -s tools
godot --headless --path game --editor --import --quit
godot --headless --path game --script res://tests/suite.gd
bash tools/build_web.sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory build
```

Abra `http://127.0.0.1:8765` e clique em **Iniciar jogo**. O jogo grava controles, compensação e recordes no armazenamento local do Godot. Em **Configurações → Volumes**, ajuste o acompanhamento, a bateria virtual, o metrônomo e as batidas do jogador separadamente. Em Configurações, ajuste a compensação manualmente ou toque junto a pelo menos três pulsos da calibração. Um valor positivo compensa toques registrados depois do pulso.

**Aprender ritmos** permite ajustar BPM e repetir o exercício com metrônomo. **Ensaio** permite escolher a música inteira ou um trecho, repetir o trecho e reduzir a velocidade a 75% mantendo a altura. O cabeçalho da partida mostra o ritmo durante a contagem e atualiza na transição. **Apresentação** silencia a caixa virtual e preserva os sons de feedback. **Treinar transições** inicia quatro pulsos antes da mudança para o Cortejo B e encerra quatro pulsos depois.

O teste de navegador fica em `tools/browser_test.cjs`. Instale Playwright no ambiente Node, rode `npx playwright install chromium firefox` e execute `node tools/browser_test.cjs` com o servidor local aberto. Use `NODE_PATH` se o pacote estiver em outro diretório e `FOGO_BROWSER=chromium` ou `FOGO_BROWSER=firefox` para escolher um motor. `FOGO_BROWSER=chromium FOGO_MOBILE=1` usa viewport móvel com navegação por toque. Para repetir no WebKit, instale-o com `npx playwright install webkit` e use `FOGO_BROWSER=webkit FOGO_MOBILE=1`.

## Inventário e processamento local

Instale FFmpeg e FFprobe. Para separação em CPU, instale primeiro PyTorch e TorchAudio compatíveis. A versão 2.5.1 mantém a interface de áudio usada pelo Demucs.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python tools/catalog_assets.py
python tools/analyze_repertoire.py
python tools/analyze_repertoire.py --only ensemble
python tools/suggest_transitions.py eva lucro vermelho
python tools/analyze.py 'Levadas da Percussão 2026/Caixa/Marchinha - Caixa (iniciante).mp4' --rhythm marchinha --difficulty beginner
git clone https://github.com/SysAdminDoc/Tunerize.git .local/Tunerize
git -C .local/Tunerize checkout 059224e7d4e91c244c2ae99707ea7f5eeaef75f7
python tools/convert_chiptune.py 'musicas/Alalaô.mp3' --tunerize .local/Tunerize
# Para converter todas as gravações disponíveis usando o cache local
python tools/convert_repertoire.py --tunerize .local/Tunerize
```

O catálogo gera manifestos locais para as sete entradas do repertório, inclusive Bloco na Rua. O lote de análise estima pulsos, andamento, tonalidade e ataques nas gravações e nos vídeos de caixa dos ritmos oficiais. A similaridade de ataques quantizados propõe trechos de repetição para revisão. A grade inicial assume quatro pulsos subdivididos em quatro apenas para comparar janelas candidatas. Compassos, mãos, acentos e técnicas exigem revisão.

A conversão usa Demucs para separar os stems, Basic Pitch para transcrever voz, baixo e outros instrumentos, e o renderizador SNES do Tunerize para sintetizar a mistura MIDI. O código do Tunerize possui CLI de conversão e módulo de síntese. O pipeline usa o módulo após descartar o stem de bateria, preserva os tempos em segundos e exporta MIDI, WAV, OGG e relatório. O MIDI inclui um mapa de tempo estimado e aceita até oito notas simultâneas. Os pulsos estimados e a contagem de notas descartadas ficam no relatório. Informe `--transpose N` só depois de confirmar os semitons necessários. O cache usa SHA-256 do áudio, revisão do analisador ou conversor e parâmetros do arranjo. Artefatos são privados em `.local/`.

## Testar o repertório do bloco no navegador

Gere o build com `bash tools/build_web.sh` e execute `python3 tools/serve_local_web.py`. Abra [o ensaio local](http://127.0.0.1:8766/?bloco=1) e clique em **Iniciar jogo**. O servidor atualiza o catálogo ao iniciar, escuta apenas em loopback e serve as gravações sob demanda. O PCK verificado continua contendo apenas a demonstração pública.

## Seleção local do bloco

Execute `python tools/index_local_repertoire.py` depois de analisar ou converter gravações. Ao abrir o projeto Godot, o catálogo local lista as faixas do bloco e os ritmos candidatos. As faixas de levada única com arranjo convertido e mapa candidato ficam disponíveis para partida experimental. Faixas com mudanças ainda sem timestamps oferecem audição local e mostram a ordem catalogada das levadas.

## Revisar mapas e testar Alalaô

Para revisar uma música, abra o [editor do servidor local](http://127.0.0.1:8766/__bloco/editor), escolha a faixa, abra **Comparar levada** nos pontos de troca e use **Salvar no jogo local** após marcar **Revisado e aprovado**. Use **Salvar rascunho** para retomar uma revisão parcial, seja de tempos ou de uma levada. Reabra o jogo local para carregar tempos já aprovados. Para usar arquivos avulsos, abra `tools/editor.html` diretamente no navegador. Carregue o vídeo ou o WAV extraído, o `analysis.json` e o arquivo de mapa candidato ou manifesto. A forma de onda permite navegar por clique. Ajuste BPM, compasso, intervalo e loop. Corrija as notas e indique mãos, acentos e técnicas. Para revisar transições de uma música, carregue seu manifesto e use os campos de tempo ou posicione o cursor antes de clicar em **Usar cursor**. Marque **Revisado e aprovado** e exporte o JSON. O editor pode mostrar os pulsos da análise e ajustar o cursor ao pulso estimado mais próximo. Execute `python3 tools/index_local_repertoire.py --review CAMINHO_DO_JSON` para disponibilizar a sequência no jogo local e reinicie o servidor de ensaio. A aprovação dos tempos é independente da revisão dos mapas e da autorização para publicação.

Com o acompanhamento convertido e o mapa:

```sh
python tools/prepare_playtest.py CAMINHO_DO_ARRANJO CAMINHO_DO_MAPA.json
godot --path game
```

Alalaô aparece como **experimental** em Jogar. Para preparar outra faixa, passe `--song ID`. Se a faixa tiver mais de uma levada, use `--manifest` com o JSON revisado e forneça um arquivo de mapa por ritmo na mesma chamada. As faixas preparadas ficam disponíveis juntas na seleção local de músicas. O editor e a execução local preservam a ordem catalogada. Notas com mão desconhecida aparecem no centro e aceitam qualquer baqueta. O protótipo usa a primeira batida e o mapa de andamento estimados. A versão oficial requer confirmação humana da grade, levada e arranjo. Consulte [inventário](docs/ASSET_INVENTORY.md), [progresso](docs/PROGRESS.md) e [autorizações](docs/LICENCES.md).

## Aprovar levadas de instrumentos

No [editor local](http://127.0.0.1:8766/__bloco/editor), escolha uma opção em **Vídeo de levada** para carregar a referência, a forma de onda e seu candidato. Depois da revisão, **Salvar no jogo local** atualiza o catálogo imediatamente. Para trabalhar com arquivos avulsos, carregue o vídeo de referência, seu `analysis.json` e o JSON candidato correspondente. Use **Ver quadros** para comparar imagens antes e depois de cada ataque. Revise a grade e as notas, incluindo mão, acento e técnica. Marque **Revisado e aprovado** e exporte o mapa. Execute `python3 tools/index_local_repertoire.py --pattern CAMINHO_DO_MAPA` e reabra o jogo local. O importador verifica o identificador, instrumento, ritmo, dificuldade e hash da referência. Combinações aprovadas de repique e surdos aparecem em **Aprender ritmos**, com timbre próprio. Para navegador, reinicie o servidor local após importar.

## Publicação

Para preparar a edição pública do bloco, conclua as revisões de tempos e mapas e registre as autorizações conforme [Autorizações](docs/LICENCES.md). Com os arquivos autorizados, rode `python3 tools/build_repertoire.py .local/release-web` em uma pasta de saída nova. Essa edição usa o repertório do bloco e exporta os áudios permitidos fora do PCK. Use um servidor estático para testar o artefato. Antes do envio, rode `python3 tools/build_repertoire.py .local/release-web --verify-only` para conferir novamente o catálogo, o PCK e os hashes dos OGG.


No repositório GitHub, selecione **GitHub Actions** em **Settings → Pages → Build and deployment**. O workflow executa os testes em pushes para `main`, pull requests e execuções manuais. A publicação ocorre apenas na branch `main`. Os caminhos Web são relativos e o artefato contém apenas os arquivos da exportação pública. O build pode também ser servido por hospedagem estática.

## Referências técnicas

- [Sincronização com áudio no Godot](https://docs.godotengine.org/en/stable/tutorials/audio/sync_with_audio.html)
- [Exportação Web do Godot 4.5 e modos de reprodução](https://docs.godotengine.org/en/4.5/tutorials/export/exporting_for_web.html)
- [Código do sintetizador Tunerize no commit inspecionado](https://github.com/SysAdminDoc/Tunerize/blob/059224e7d4e91c244c2ae99707ea7f5eeaef75f7/app/core/chiptune.py)
