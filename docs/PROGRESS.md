# Progresso do FogonuHero

## Entregue

- Inventário de seis MP3 e 59 vídeos, com FFprobe e leitura integral de `notas.md`. O catálogo registra Bloco na Rua sem áudio e preserva as sequências rítmicas na ordem informada.
- **Cortejo de Neon**, demonstração pública original com caixa de guerra, duas pistas, dois níveis, teclado configurável, multitoque, acentos, pontuação, combo, multiplicador, precisão e resultados por mão e ritmo.
- Modos Aprender, Ensaio, Apresentação e Treinar transições na demonstração. O HUD exibe o ritmo durante a contagem e muda no instante da transição. O ensaio permite selecionar e repetir um trecho e praticar a 75% com altura preservada. Calibração manual ou por pulsos, janelas ajustáveis, recordes locais, pausa e retomada.
- Relógio baseado na posição de reprodução. No navegador, Godot usa reprodução Sample via Web Audio. O desenvolvimento nativo usa Stream com interpolação entre mixes. Ambos compensam latência e pausam quando o áudio deixa de avançar.
- Pipeline local com extração, estimativa de BPM, grade de pulsos, tonalidade, transientes e comparação de repetições. Rodou nas seis músicas e em 13 vídeos de caixa cobrindo os oito ritmos do repertório. O índice local aponta os relatórios e candidatos. Foram analisados também 22 vídeos de repique e surdos com instrumento e ritmo identificáveis pelo nome, para revisão local.
- Conversão e protótipo experimental local de **Alalaô**, com acompanhamento sintetizado e candidato em pulsos derivado do vídeo de Marchinha para iniciantes. O arranjo tem 196,406 s e chegou a oito vozes simultâneas no MIDI, com 39 eventos de tempo estimados. O relatório e os arquivos MIDI, WAV e OGG ficam em `.local/arrangements/`. A preparação local coloca os arquivos consumidos pelo Godot em `.local/playtest/`.
- Editor de forma de onda, grade, áudio/vídeo, transições, mãos, acentos, técnicas e exportação. A aprovação depende da revisão manual.
- Exportação release Web single-thread em `build/`, com Godot 4.5.1 e templates correspondentes. A lista de recursos é validada antes da exportação e no índice interno do PCK. O áudio público tem autorização vinculada ao SHA-256. O workflow Pages executa testes e publica somente a partir de `main`.

## Verificação executada

| Ambiente | Resultado |
|---|---|
| Python 3.10 | Testes de manifesto, rascunhos, erros de limites, áudio ausente e substituição de áudio público |
| Godot 4.5.1 headless Linux | Carregamento, mudanças de andamento, transições, pontuação, janelas, compensação, multitoque simultâneo, BPM de prática, pausa e retomada |
| Chromium Linux via Playwright | Inicialização WebGL/WASM, navegação, partida, pausa durante reprodução, retomada, envio de teclado e toque, tela de resultado |
| Firefox Linux via Playwright | Mesmo fluxo, com WebGL por software e saída PulseAudio virtual no ambiente WSL |
| Editor no Chromium | Abertura de WAV e mapa candidato, bloqueio de aprovação com dados desconhecidos, exportação de rascunho e abertura de manifesto com dez transições |
| Alalaô no Godot headless | Carregamento do OGG privado, seleção programática do protótipo e geração do mapa experimental |
| Build release local | WASM, worklets de áudio e todos os caminhos do índice do PCK conferidos |

A navegação por toque em viewport móvel passou no Chromium emulado. Chrome Android, Safari iOS, latência física e toque simultâneo em aparelho real aguardam teste. A demonstração está publicada no [GitHub Pages](https://9kernel.github.io/fogonuhero/). O [repositório de publicação](https://github.com/9kernel/fogonuhero) contém apenas o build Web e o arquivo de configuração do Pages. O Pages publica a raiz da branch `main`. O workflow de exportação continua disponível neste workspace para desenvolvimento.

## Pendências de repertório

- Confirmar os timestamps das transições das músicas e revisar as estimativas de andamento e tonalidade.
- Revisar mãos, acentos, compasso e técnicas dos candidatos com as referências do professor. Repique e surdos seguem indisponíveis como instrumentos jogáveis. Os sons de repique e surdo na demonstração fazem parte do acompanhamento original de Cortejo de Neon.
- Avaliar de ouvido os arranjos experimentais de Alalaô e Vou Festejar. A separação pode deixar vestígios de bateria nos stems melódicos. Concluir os arranjos completos das outras gravações e confirmar autorizações.
- O analisador identifica grupos densos de ataques e repetição. A identificação de viradas, rulos, chamadas e mãos continua manual. Rastreamento de movimento, MIDI e gamepad seguem pendentes.

## Atualização do ensaio

- A revisão pública `b37fc9e` foi testada no Chromium até a tela de resultado, incluindo a mudança de Cortejo A para Cortejo B.
- Alalaô e Vou Festejar foram preparados e carregados no Godot como faixas experimentais privadas, com as versões a 75% e candidatos de Marchinha e Samba.
- O processamento local das outras faixas foi iniciado. Os relatórios concluídos ficam em `.local/arrangements/`.

## Catálogo do bloco

- A seleção local lista as seis gravações e registra Bloco na Rua como áudio ausente. A seleção local de músicas e ritmos usa o repertório do bloco.
- Alalaô, Vou Festejar e Bella Ciao carregam como partidas experimentais. Eva, Lucro e Vermelho têm audição local enquanto os instantes de transição aguardam revisão.
- O catálogo privado e os materiais associados permanecem fora do PCK e do GitHub Pages.

## Repertório no navegador local

- As seis gravações disponíveis têm acompanhamento convertido. O servidor local carrega os arranjos sob demanda e exibe as três partidas experimentais de levada única.
- O Chromium confirmou as seis entradas com áudio e abriu Bella Ciao com Maculelê no cabeçalho da partida.
- A publicação permanece na revisão pública b37fc9e. O catálogo privado roda em loopback e fica fora do PCK aprovado para publicação.

## Revisão dos tempos de mudança

- O editor mostra os pulsos estimados da análise, permite aproximar a reprodução do ponto de troca e oferece ajuste opcional do cursor ao pulso.
- O importador aceita apenas tempos explicitamente aprovados para a mesma gravação e na ordem catalogada. As revisões ficam em `.local/reviews/`, com o manifesto original preservado. Quando houver arranjo e candidatos para todas as levadas, a importação prepara a faixa para o ensaio e o treino de transições.
- Testes Python, Godot e Chromium passaram, incluindo uma revisão sintética com tempos não uniformes e a persistência da importação. As transições reais de Eva, Lucro e Vermelho seguem pendentes de evidência e revisão.

- O editor do servidor local carrega o manifesto, os pulsos, a forma de onda e a gravação original ao escolher uma faixa. O áudio permite navegação por trechos. Uma revisão aprovada pode atualizar o catálogo local pela própria interface.
- No Chromium, Lucro abriu com as dez entradas e áudio navegável. O editor bloqueou uma tentativa com campos vazios. Um teste HTTP isolado aplicou tempos sintéticos aprovados e rejeitou gravação a partir de outra origem.

## Levada por instrumento

- A biblioteca privada aceita mapas aprovados de caixa, repique e surdos vinculados à referência analisada. O modo Aprender lista os instrumentos, ritmos e níveis que têm mapa aprovado. O som do toque e o som de referência seguem o instrumento selecionado.
- O teste Godot percorreu a seleção e iniciou Ijexá de repique com um mapa sintético, confirmando a grade, o andamento e o timbre. O teste Python rejeitou mapas em rascunho e hashes divergentes.
- O catálogo real permanece sem mapas aprovados de repique e surdos. As faixas com múltiplos ritmos ainda aguardam revisão de seus tempos.

## Sugestões acústicas para revisão

- O analisador de transições compara janelas de quatro pulsos usando ataques subdivididos e energia por banda. Gerou 24 pontos de escuta para Eva, 21 para Lucro e 19 para Vermelho. As sugestões aparecem na forma de onda e permitem pular para o trecho.
- Um teste sintético localizou a mudança esperada e descartou sinal sem contraste. No Chromium, clicar em uma sugestão de Vermelho posicionou o áudio e manteve os quatro tempos do manifesto em branco.
- Cada sugestão indica uma mudança acústica. A levada e o instante da transição ainda exigem conferência musical.

- O editor local lista 35 referências de caixa, repique e surdos. Selecionar uma referência carrega o vídeo e o candidato correspondente. O mapa aprovado pode ser salvo pelo navegador e entra no catálogo sem reiniciar o servidor.
- O Chromium carregou a referência de Ijexá para repique, recebeu o trecho solicitado e confirmou o bloqueio de um rascunho. Um teste HTTP isolado confirmou que um mapa sintético aprovado chega ao catálogo do jogo.

## Exportação da edição do bloco

- Foi implementado um build separado para a edição do bloco. Ele exige revisão dos tempos e autorização por hash para os arranjos e padrões didáticos. O PCK da edição não carrega a demonstração nem os arranjos. Apenas o catálogo e os OGG autorizados são adicionados ao site.
- Um build de teste sem acervo real abriu em subdiretório no Chromium, carregou o áudio, mostrou Samba no cabeçalho e chegou ao resultado. Os testes também rejeitaram mapa sem autorização e áudio alterado.
- O build do repertório real permanece bloqueado no preflight pela falta das autorizações. A versão em produção continua na revisão b37fc9e.

## Bateria virtual por instrumento

- No repertório do bloco, a bateria virtual usa as levadas aprovadas disponíveis para caixa, repique e surdos. Cada instrumento tem seu próprio timbre e cursor vinculado ao tempo da música. Um instrumento com mapa parcial acompanha apenas os trechos aprovados e só aparece para o jogador quando cobre a faixa inteira.
- Ensaios incluem a parte do jogador. Apresentação mantém as camadas dos demais instrumentos e deixa a parte do jogador para os toques.
- A suíte Godot verificou camadas simultâneas com dados de teste, mapa parcial, seleção com cobertura completa e o comportamento de Ensaio e Apresentação. O catálogo real segue sem os mapas aprovados necessários para habilitar essas camadas.

## Verificação móvel emulada

- A tela inicial do ensaio local identifica o repertório do bloco e oferece acesso direto ao editor.
- Chromium e WebKit no Linux completaram, em viewport móvel e com toque emulado, a demonstração com carregamento, partida, pausa, retomada, transição de ritmo e resultado.
- A lista do ADB estava vazia. Essa execução emulada deixa pendentes Safari iOS e Chrome Android em aparelhos reais, inclusive medições físicas de latência.
- O WebKit em viewport móvel também abriu o ensaio privado, conferiu as seis gravações no catálogo e iniciou Bella Ciao com Maculelê na partida.

## Desempenho da partida em faixas longas

- O motor busca por tempo somente as notas na janela de acerto ou na área visível. Um cursor avança pelo mapa ao registrar atrasos, mantendo o relógio de áudio como referência.
- No Godot, um teste com 7.200 notas confirmou um acerto perto do fim da faixa e verificou que os atrasos anteriores são registrados uma única vez.

## Níveis e escolha de transições

- O repertório oferece um nível por música quando há mapa desse nível para todos os trechos do instrumento. Se os mapas disponíveis têm níveis diferentes, a opção usa a identificação `Mapas disponíveis`.
- O treino mostra o nome das levadas de origem e destino. Para faixas com várias trocas, a opção mostra também a posição no repertório.
- O teste Godot verificou níveis incompletos, escolha de mapa avançado com janela de acerto correspondente e identificação da transição. O build público aplica a mesma regra aos níveis descritos no catálogo.

## Controles de volume

- Configurações → Volumes oferece seis ajustes independentes para acompanhamento, caixa virtual, repique virtual, surdos virtuais, metrônomo e batidas do jogador. As preferências ficam no armazenamento local do Godot.
- O teste Godot confirmou o ajuste em decibéis, a alteração das preferências e o silenciamento de um canal sem afetar o feedback.

## Comparação de levadas e gravações

- Cada entrada do manifesto pode abrir uma comparação com os vídeos da levada correspondente. A interface prioriza as referências de caixa e alterna o áudio da música e do vídeo. A comparação não escreve tempos no mapa.
- No Chromium, a segunda entrada de Eva abriu a comparação Ijexá → Samba-reggae. O teste alternou os dois áudios e confirmou que os seis tempos ainda estavam vazios.

- A edição pública do bloco agora tem verificação independente do pacote exportado. Ela confere o catálogo e os hashes autorizados, rejeita arquivos extras e links simbólicos e exige o marcador vazio do GitHub Pages.
- O teste com a exportação sintética passou e detectou um vídeo extra e uma troca de OGG após a exportação. O catálogo real ainda lista três partidas experimentais e não recebeu autorizações nem novos tempos revisados.

## Quadros para revisão de mãos e técnicas

- No editor local, uma batida de um vídeo catalogado pode mostrar três quadros do FFmpeg em torno de seu tempo na grade. Os quadros são extraídos sob demanda e mantidos em cache em memória.
- O Chromium confirmou três imagens distintas em Marchinha para caixa. A mão desconhecida permaneceu intacta. A ferramenta apoia a revisão visual e os mapas reais continuam pendentes.

- Na aula de Marchinha para caixa iniciante, a comparação quadro a quadro indicou mão esquerda perto de 6,223 s e mão direita perto de 7,407 s. São observações provisórias do vídeo. As sete notas do candidato ainda têm mão desconhecida e nenhuma técnica ou acento foi aprovado nessa revisão.
- O Chromium confirmou que o editor mostra os dois indícios e os oculta quando o intervalo é reposicionado para longe da evidência.

## Revisões em mais de uma sessão

- O editor salva e recupera rascunhos de transições e de levadas, vinculados ao hash da referência. Os rascunhos são privados e ficam fora do catálogo jogável até a aprovação.
- Em servidor isolado com dados de teste, o Chromium recuperou uma revisão parcial de Lucro e uma anotação parcial de Marchinha após recarregar. A partida de Lucro e o estado de aprovação da Marchinha permaneceram inalterados.
