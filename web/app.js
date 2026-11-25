const canvas = document.querySelector('#canvas');
const start = document.querySelector('#start');
const status = document.querySelector('#status');
const progress = document.querySelector('#progress');
const fullscreen = document.querySelector('#fullscreen');
const localRepertoire = ['127.0.0.1', 'localhost'].includes(location.hostname)
  && new URLSearchParams(location.search).get('bloco') === '1';
if (localRepertoire) {
  document.querySelector('#intro').textContent = 'Toque as levadas do bloco em duas pistas.';
  document.querySelector('#credits').textContent = 'Repertório local do bloco';
  document.querySelector('#review-link').hidden = false;
}
canvas.addEventListener('contextmenu', event => event.preventDefault());
start.addEventListener('click', async () => {
  start.disabled = true;
  progress.hidden = false;
  status.textContent = 'Carregando o jogo…';
  try {
    if (typeof Engine === 'undefined' || !Engine.isWebGLAvailable()) {
      throw new Error('WebGL 2 ou o carregador do jogo está indisponível.');
    }
    const engine = new Engine({ executable: 'index', canvas, canvasResizePolicy: 2,
      onProgress(loaded, total) {
        if (total > 0) {
          progress.max = total;
          progress.value = loaded;
        }
      } });
    await engine.startGame();
    document.querySelector('#welcome').hidden = true;
    fullscreen.hidden = !document.fullscreenEnabled;
    canvas.focus();
  } catch (error) {
    status.textContent = 'Falha ao iniciar. Recarregue a página. ' + error.message;
    progress.hidden = true;
  }
});
fullscreen.addEventListener('click', async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch {
    fullscreen.hidden = true;
  }
  canvas.focus();
});
