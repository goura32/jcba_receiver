const elements = {
  audio: document.querySelector('#audio'), list: document.querySelector('#station-list'), search: document.querySelector('#search'),
  chips: document.querySelector('#region-chips'), name: document.querySelector('#station-name'), prefecture: document.querySelector('#station-prefecture'),
  region: document.querySelector('#station-region'), count: document.querySelector('#station-count'), play: document.querySelector('#play-button'),
  playIcon: document.querySelector('#play-icon'), state: document.querySelector('#stream-state'), notice: document.querySelector('#notice'),
  favorite: document.querySelector('#favorite-button'), favoritesFilter: document.querySelector('#favorites-filter'), volume: document.querySelector('#volume'),
  mute: document.querySelector('#mute-button'), wave: document.querySelector('#wave'), programTitle: document.querySelector('#program-title'),
  programPerformer: document.querySelector('#program-performer'), programDetail: document.querySelector('#program-detail'),
};
const state = { stations: [], selected: null, region: '', query: '', favoritesOnly: false, playbackId: 0, favorites: new Set(JSON.parse(localStorage.getItem('jcba-favorites') || '[]')) };
const regions = ['すべて', '北海道', '東北', '関東', '甲信越', '東海', '近畿', '中国', '四国', '九州'];
function saveFavorites() { localStorage.setItem('jcba-favorites', JSON.stringify([...state.favorites])); }
function status(label, notice = '', error = false) { elements.state.textContent = label; elements.notice.textContent = notice; elements.notice.classList.toggle('error', error); }
function filtered() { const needle = state.query.toLocaleLowerCase(); return state.stations.filter(s => (!state.region || s.region === state.region || s.prefecture.includes(state.region)) && (!state.favoritesOnly || state.favorites.has(s.id)) && (!needle || `${s.name} ${s.prefecture} ${s.region}`.toLocaleLowerCase().includes(needle))).sort((a,b) => Number(state.favorites.has(b.id)) - Number(state.favorites.has(a.id)) || a.name.localeCompare(b.name, 'ja')); }
function renderChips() { elements.chips.innerHTML = regions.map(region => `<button class="chip ${(!state.region && region === 'すべて') || state.region === region ? 'active' : ''}" data-region="${region}">${region}</button>`).join(''); elements.chips.querySelectorAll('.chip').forEach(button => button.addEventListener('click', () => { state.region = button.dataset.region === 'すべて' ? '' : button.dataset.region; render(); })); }
function render() {
  renderChips();
  const stations = filtered();
  elements.list.replaceChildren();
  if (!stations.length) {
    const empty = document.createElement('p');
    empty.className = 'notice';
    empty.textContent = '条件に合う局がありません。';
    elements.list.append(empty);
  }
  stations.forEach(station => {
    const button = document.createElement('button');
    button.className = `station-item ${state.selected?.id === station.id ? 'selected' : ''}`;
    button.dataset.id = station.id;
    const text = document.createElement('span');
    const name = document.createElement('strong');
    name.textContent = station.name;
    const detail = document.createElement('small');
    detail.textContent = `${station.prefecture} · ${station.region}`;
    text.append(name, detail);
    const star = document.createElement('span');
    star.className = 'star';
    star.textContent = state.favorites.has(station.id) ? '★' : '';
    button.append(text, star);
    button.addEventListener('click', () => selectStation(station.id));
    elements.list.append(button);
  });
  elements.favoritesFilter.setAttribute('aria-pressed', String(state.favoritesOnly));
}
async function selectStation(id) { const station = state.stations.find(s => s.id === id); if (!station) return; if (elements.audio.currentSrc) stop(); state.selected = station; elements.name.textContent = station.name; elements.prefecture.textContent = `${station.prefecture} · ${station.region}`; elements.region.textContent = station.id.toUpperCase(); elements.favorite.setAttribute('aria-pressed', String(state.favorites.has(id))); elements.favorite.textContent = state.favorites.has(id) ? '★' : '☆'; elements.programTitle.textContent = '番組情報を取得中'; elements.programPerformer.textContent = 'この局が情報を提供している場合に表示されます。'; elements.programDetail.textContent = ''; status('READY', '再生ボタンでライブ受信を開始します。'); render(); try { const response = await fetch(`/api/programs/${id}`); const { program } = await response.json(); if (state.selected?.id !== id) return; elements.programTitle.textContent = program?.title || '番組情報はありません'; elements.programPerformer.textContent = program?.performer || '現在の番組情報は提供されていません。'; elements.programDetail.textContent = program?.detail || ''; } catch { if (state.selected?.id === id) elements.programTitle.textContent = '番組情報を取得できません'; } }
async function play() { if (!state.selected) { status('STANDBY', 'まず放送局を選択してください。', true); return; } if (!elements.audio.paused) return stop(); const playbackId = ++state.playbackId; const stationId = state.selected.id; status('CONNECTING', 'ライブ配信へ接続しています。'); elements.audio.src = `/api/stream/${stationId}?t=${Date.now()}`; elements.audio.load(); try { await elements.audio.play(); if (playbackId !== state.playbackId || stationId !== state.selected?.id) return; } catch { if (playbackId === state.playbackId) status('ERROR', '再生を開始できませんでした。もう一度お試しください。', true); } }
function stop() { state.playbackId += 1; elements.audio.pause(); elements.audio.removeAttribute('src'); elements.audio.load(); elements.playIcon.textContent = '▶'; elements.play.setAttribute('aria-label', '再生'); elements.wave.classList.remove('playing'); status('STOPPED', '再生を停止しました。'); }
elements.audio.addEventListener('playing', () => { elements.playIcon.textContent = '■'; elements.play.setAttribute('aria-label', '停止'); elements.wave.classList.add('playing'); status('PLAYING', 'ライブ音声を受信中です。'); }); elements.audio.addEventListener('waiting', () => { if (!elements.audio.paused) status('BUFFERING', 'バッファリングしています。'); }); elements.audio.addEventListener('error', () => { if (elements.audio.error) status('UNAVAILABLE', '現在この局の配信を受信できません。時間をおいて再試行してください。', true); }); elements.play.addEventListener('click', play); elements.favorite.addEventListener('click', () => { if (!state.selected) return; const id = state.selected.id; state.favorites.has(id) ? state.favorites.delete(id) : state.favorites.add(id); saveFavorites(); selectStation(id); }); elements.favoritesFilter.addEventListener('click', () => { state.favoritesOnly = !state.favoritesOnly; render(); }); elements.search.addEventListener('input', event => { state.query = event.target.value; render(); }); elements.volume.addEventListener('input', event => { elements.audio.volume = event.target.value / 100; }); elements.mute.addEventListener('click', () => { elements.audio.muted = !elements.audio.muted; elements.mute.textContent = elements.audio.muted ? '◌' : '◖'; });
(async function init() { try { const response = await fetch('/api/stations'); const data = await response.json(); state.stations = data.stations; elements.count.textContent = `${data.count} STATIONS`; render(); const initial = state.stations.find(s => s.id === 'fmnanami') || state.stations[0]; if (initial) selectStation(initial.id); const refreshed = await fetch('/api/stations?refresh=true'); const refreshedData = await refreshed.json(); state.stations = refreshedData.stations; state.selected = state.stations.find(s => s.id === state.selected?.id) || state.selected; elements.count.textContent = `${refreshedData.count} STATIONS`; render(); } catch { status('ERROR', '局一覧を取得できませんでした。ページを再読み込みしてください。', true); } })();
