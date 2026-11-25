# Autorizações de distribuição

| Material | Situação | Destino |
|---|---|---|
| Cortejo de Neon, composição e gravação sintetizada | CC0-1.0 | Build público |
| Cortejo A e B, padrões originais da demonstração | CC0-1.0 | Build público |
| Clique, caixa, repique e surdo sintetizados pelo jogo | CC0-1.0 | Build público |
| MP3 do repertório, separações, transcrições MIDI e arranjos derivados | Autorização de distribuição pendente | Uso local |
| Vídeos didáticos, áudios extraídos e mapas candidatos | Autorização de distribuição pendente | Uso local |
| Tunerize | MIT, dependência local no commit documentado | Código obtido separadamente |
| Godot e templates | MIT e avisos de terceiros presentes na distribuição do motor | Runtime Web |

Os padrões do Cortejo são exercícios originais da demonstração. A autorização de uma conversão ou transcrição do repertório precisa ser verificada independentemente do formato de saída.

O exportador copia apenas os caminhos enumerados em `tools/validate_assets.py` para um projeto temporário. Qualquer mudança dessa lista exige revisão do material e da autorização. O catálogo resumido registra nomes relativos dos arquivos. O inventário detalhado do FFprobe e os dados das gravações ficam em `.local/`.

A autorização verificável do áudio público e o SHA-256 do arquivo constam em [publication.json](publication.json).

## Edição pública do bloco

A edição pública do bloco exige autorizações documentadas para cada arranjo e mapa usados.
O campo `repertoire` em `publication.json` usa o identificador da música e exige
`authorized: true`, `license`, `permission_reference` e o `sha256` do OGG. Para incluir
a versão lenta, registre também `slow_sha256`. O campo `patterns` usa o identificador do
mapa e exige os mesmos campos de aprovação. O hash do mapa é calculado por
`pattern_checksum` em `tools/build_repertoire.py` a partir de sua representação pública.

O build carrega o catálogo e somente os OGG autorizados por caminhos relativos. O índice
do PCK é conferido separadamente e fica sem as mídias. Os campos de autorização e as
referências de origem permanecem no workspace.

O comando de verificação do pacote final confere os OGG com os hashes autorizados, compara o catálogo exportado com a revisão local e rejeita arquivos extras e links simbólicos.
