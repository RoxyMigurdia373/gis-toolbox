'use strict';
const $ = id => document.getElementById(id);
const cards = new Map();
const seenErrors = new Map();
let api;
let polling = false;

function message(text, error = false) {
  $('message').textContent = text;
  $('message').classList.toggle('error', error);
  $('message').hidden = !text;
}

function update(states) {
  let active = 0;
  for (const [id, state] of Object.entries(states)) {
    const card = cards.get(id);
    if (!card) continue;
    const opening = state.status === 'starting' || state.status === 'closing';
    const running = state.status === 'running';
    if (opening || running) active++;
    card.open.disabled = opening;
    card.open.textContent = state.status === 'starting' ? '正在启动…' : state.status === 'closing' ? '正在关闭…' : running ? '已打开 · 切换窗口 ↗' : '打开工具 ↗';
    card.close.hidden = !running;
    card.status.textContent = {starting:'启动中', closing:'关闭中', running:'运行中', error:'启动异常', closed:'可使用'}[state.status] || state.status;
    card.status.className = `pill ${state.status}`;
    if (state.error && seenErrors.get(id) !== state.error) {
      message(state.error, true);
      seenErrors.set(id, state.error);
    }
    if (!state.error) seenErrors.delete(id);
  }
  $('summary').textContent = `${cards.size} 个工具 · ${active ? `${active} 个正在使用` : '准备就绪'}`;
}

async function invoke(action) {
  try {
    const result = await action();
    if (result && !result.ok) message(result.error || '操作失败，请查看日志。', true);
    else if (result?.notice) message(result.notice);
    return result;
  } catch (error) {
    message(`操作失败：${error.message || error}`, true);
  }
}

async function poll() {
  if (polling) return;
  polling = true;
  try { update(await api.get_states()); }
  catch (_) { /* 关闭或窗口销毁期间不重复弹错 */ }
  finally { polling = false; }
}

async function init() {
  api = window.pywebview.api;
  try {
    const data = await api.get_tools();
    $('app-name').textContent = data.name;
    $('version').textContent = `v${data.version} · 本地桌面版`;
    $('about-version').textContent = `版本 ${data.version}`;
    $('tools').replaceChildren();
    for (const tool of data.tools) {
      const card = document.createElement('article');
      card.className = 'card';
      const top = document.createElement('div'); top.className = 'card-top';
      const icon = document.createElement('img'); icon.className = 'tool-icon'; icon.src = tool.icon; icon.alt = '';
      const status = document.createElement('span'); status.className = 'pill';
      top.append(icon, status);
      const title = document.createElement('h3'); title.textContent = tool.name;
      const description = document.createElement('p'); description.textContent = tool.description;
      const actions = document.createElement('div'); actions.className = 'actions';
      const open = document.createElement('button'); open.className = 'open';
      const close = document.createElement('button'); close.className = 'close'; close.textContent = '关闭'; close.hidden = true;
      open.onclick = async () => {
        open.disabled = true; open.textContent = '正在打开…'; message('');
        await invoke(() => api.open_tool(tool.id)); await poll();
      };
      close.onclick = async () => {
        close.disabled = true;
        await invoke(() => api.close_tool(tool.id)); await poll();
        close.disabled = false;
      };
      actions.append(open, close); card.append(top, title, description, actions); $('tools').append(card);
      cards.set(tool.id, {open, close, status});
    }
    update(Object.fromEntries(data.tools.map(tool => [tool.id, tool])));
    setInterval(poll, 1000);
  } catch (error) { message(`无法加载工具：${error.message || error}`, true); }
}

$('logs').onclick = () => invoke(() => api.open_logs());
$('quit').onclick = () => invoke(() => api.quit_app());
$('about').onclick = () => $('about-dialog').showModal();
$('close-about').onclick = () => $('about-dialog').close();
window.addEventListener('pywebviewready', init, {once:true});
setTimeout(() => { if (!api) message('未连接到桌面服务，请通过 GISToolbox.exe 或 launcher.py 打开本程序。', true); }, 12000);
