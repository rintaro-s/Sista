import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Config
# Default to backend host port 8030 per user request. Can be overridden with API_BASE env var.
API_BASE = os.getenv('API_BASE', 'http://localhost:8030')
st.set_page_config(page_title='Sista', layout='centered', initial_sidebar_state="collapsed")

# Ensure session fields
if 'token' not in st.session_state:
    st.session_state.token = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'auth_rerun_done' not in st.session_state:
    st.session_state.auth_rerun_done = False
if 'tasks_cache' not in st.session_state:
    st.session_state.tasks_cache = None
if 'local_chats' not in st.session_state:
    st.session_state.local_chats = []
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'server_history' not in st.session_state:
    st.session_state.server_history = []
if 'compressed_memory' not in st.session_state:
    st.session_state.compressed_memory = None
if 'developer_mode' not in st.session_state:
    st.session_state.developer_mode = False
if 'over_hallu' not in st.session_state:
    st.session_state.over_hallu = False
if 'user_id' not in st.session_state:
    # default to None so we don't send a non-numeric user_id to the backend/LLM
    st.session_state.user_id = None
if 'role_sheet' not in st.session_state:
    st.session_state.role_sheet = {}


# ---------- Styles & Dev guards ----------
_STYLE = """
<style>
  .main .block-container { padding: 1rem; max-width: 1100px; }
  .header-container { background:#fff; border-bottom:1px solid #efefef; padding: .75rem 0; }
  .header-title { font-size:1.4rem; font-weight:700; margin:0 }
  .login-container{ background:#fff; border:1px solid #eee; padding:1.6rem; max-width:420px; margin:1rem auto; border-radius:6px }
  .section-header{ font-weight:600; margin-top:1.2rem; margin-bottom:.5rem; border-bottom:1px solid #f3f3f3; padding-bottom:.5rem }
  .task-card{ background:#fff; border:1px solid #eee; padding:.8rem; border-radius:6px; margin-bottom:.5rem }
  .chat-card{ background:#fbfbfb; border-left:3px solid #111; padding:.6rem; margin-bottom:.4rem }
  .user-status{ background:#111; color:#fff; padding:.4rem .6rem; border-radius:6px; text-align:center }
  .stButton>button{ background:#000; color:#fff }
</style>
"""

# Dev guard: short-circuit Segment/analytics calls in-browser (dev only)
_DEV_GUARD = """
<script>
(function(){
  try{
    const blockedHost = 'api.segment.io';
    const _fetch = window.fetch;
    window.fetch = function(resource, init){
      try{
        const url = (typeof resource === 'string') ? resource : (resource && resource.url) || '';
        if(url && url.includes(blockedHost)){
          return Promise.resolve(new Response(null, {status:0, statusText:'Blocked by dev guard'}));
        }
      }catch(e){}
      return _fetch.apply(this, arguments);
    };
    const _xhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url){
      try{ if(typeof url === 'string' && url.includes(blockedHost)){ this._dev_guard = true } }catch(e){}
      return _xhrOpen.apply(this, arguments);
    };
    const _xhrSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(){ if(this._dev_guard){ try{ this.readyState=4; this.status=0 }catch(e){}; return } return _xhrSend.apply(this, arguments) };
  }catch(e){ console.warn('dev guard failed', e) }
})();
</script>
"""

st.markdown(_STYLE, unsafe_allow_html=True)
st.markdown(_DEV_GUARD, unsafe_allow_html=True)


# ---------- API helpers ----------
def _auth_headers():
    h = {'Content-Type': 'application/json'}
    if st.session_state.token:
        h['Authorization'] = f"Bearer {st.session_state.token}"
    return h

def api_post(path, data=None, timeout=5):
    try:
        return requests.post(f"{API_BASE}{path}", json=data, headers=_auth_headers(), timeout=timeout)
    except Exception as e:
        st.error(f"Network error: {e}")
        return None

def api_get(path, timeout=5):
    try:
        return requests.get(f"{API_BASE}{path}", headers=_auth_headers(), timeout=timeout)
    except Exception as e:
        st.error(f"Network error: {e}")
        return None


# ---------- Auth ----------
def register(username, password):
    r = api_post('/auth/register', {'username': username, 'password': password})
    if not r:
        return False
    if r.status_code in (200, 201):
        st.session_state.token = r.json().get('access_token')
        st.session_state.username = username
        st.success('Registered and logged in')
        if not st.session_state.auth_rerun_done:
            st.session_state.auth_rerun_done = True
            st.rerun()
        return True
    st.error(f"Register failed: {r.status_code} {r.text}")
    return False

def login(username, password):
    r = api_post('/auth/login', {'username': username, 'password': password})
    if not r:
        return False
    if r.status_code == 200:
        st.session_state.token = r.json().get('access_token')
        st.session_state.username = username
        st.success('Logged in')
        if not st.session_state.auth_rerun_done:
            st.session_state.auth_rerun_done = True
            st.rerun()
        return True
    st.error(f"Login failed: {r.status_code} {r.text}")
    return False

def logout():
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.auth_rerun_done = False
    st.rerun()


# ---------- Domain ops ----------
def fetch_tasks():
    r = api_get('/tasks')
    tasks = []
    if r and r.status_code == 200:
        try:
            tasks = r.json()
        except Exception:
            tasks = []
    elif r and r.status_code == 401:
        st.warning('Unauthorized. Please login.')
        tasks = []
    elif not r:
        tasks = []
    else:
        st.error(f'Error fetching tasks: {r.status_code}')
        tasks = []
    st.session_state.tasks_cache = tasks
    return tasks

def create_task(text):
    r = api_post('/tasks', {'title': text, 'completed': False})
    if not r:
        # fallback: append to local cache
        now = __import__('datetime').datetime.now().isoformat()
        local = {'id': f'local-{len(st.session_state.tasks_cache or [])+1}', 'title': text, 'completed': False, 'created_at': now}
        if st.session_state.tasks_cache is None:
            st.session_state.tasks_cache = []
        st.session_state.tasks_cache.insert(0, local)
        st.success('Task created (local fallback)')
        return True
    if r.status_code in (200,201):
        st.success('Task created')
        # refresh cache
        st.session_state.tasks_cache = None
        return True
    if r.status_code == 401:
        st.warning('Unauthorized. Please login.')
        return False
    st.error(f'Create failed: {r.status_code} {r.text}')
    return False

def update_task(task_id, patch):
    try:
        r = requests.patch(f"{API_BASE}/tasks/{task_id}", json=patch, headers=_auth_headers(), timeout=5)
    except Exception as e:
        st.error(f"Network error: {e}"); return False
    if r.status_code == 200: return True
    if r.status_code == 401: st.warning('Unauthorized. Please login.'); return False
    st.error(f'Update failed: {r.status_code}'); return False

def delete_task(task_id):
    try:
        r = requests.delete(f"{API_BASE}/tasks/{task_id}", headers=_auth_headers(), timeout=5)
    except Exception as e:
        st.error(f"Network error: {e}"); return False
    if r.status_code == 200: st.success('Deleted'); return True
    if r.status_code == 401: st.warning('Unauthorized. Please login.'); return False
    st.error(f'Delete failed: {r.status_code}'); return False

def fetch_chats():
    r = api_get('/chats')
    server = []
    if r and r.status_code == 200:
        try:
            server = r.json()
        except Exception:
            server = []
    elif r and r.status_code == 401:
        st.warning('Unauthorized. Please login.')
        server = []
    elif not r:
        server = []
    else:
        st.error(f'Error fetching chats: {r.status_code}')
        server = []
    # Merge server chats with any local fallback chats (local appended to end)
    combined = (server or []) + list(st.session_state.local_chats)
    return combined

def post_chat(message):
    # Prefer calling the external LLM server at /chat following LLM_client.py format
    API_CHAT = os.getenv('API_CHAT', f"{API_BASE}/chat")
    now = __import__('datetime').datetime.now().isoformat()
    # Prepare history for payload: use messages stored in session (user/assistant)
    history_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.get('messages', []) if m.get('role') in ("user", "assistant")
    ]
    # determine a numeric user_id if possible; otherwise send null to avoid LM server 422
    uid = st.session_state.get('user_id') or st.session_state.get('username')
    uid_int = None
    try:
        if uid is not None:
            uid_int = int(uid)
    except Exception:
        uid_int = None

    payload = {
        "user_id": uid_int,
        "text": message,
        "role_sheet": st.session_state.get('role_sheet') or None,
        "over_hallucination": st.session_state.get('over_hallu', False),
        "history": history_messages,
        "compressed_memory": st.session_state.get('compressed_memory')
    }
    try:
        resp = requests.post(API_CHAT, json=payload, timeout=20, headers=_auth_headers())
    except Exception as e:
        # Network error: fallback to local mock but return False to indicate not authoritative
        st.warning(f"LLM server unreachable, falling back to local response: {e}")
        reply = 'ローカル応答: ' + ('; '.join(ai_decompose(message)) if ai_decompose(message) else '了解しました')
        st.session_state.local_chats.append({'created_at': now, 'message': f'You: {message}'})
        st.session_state.local_chats.append({'created_at': now, 'message': reply})
        # also append to messages history for UI
        st.session_state.messages.append({"role": "user", "content": message})
        st.session_state.messages.append({"role": "assistant", "content": reply})
        return False

    if resp.status_code >= 400:
        if resp.status_code == 401:
            st.warning('Unauthorized. Please login.')
            return False
        st.error(f'LLM server returned error: {resp.status_code} {resp.text}')
        return False

    try:
        data = resp.json()
    except Exception:
        data = {"response": resp.text}

    response_text = data.get('response') or data.get('reply') or data.get('message') or ''
    # Trim common prefixes
    for p in ("答え:", "回答:", "Answer:", "answer:"):
        if isinstance(response_text, str) and response_text.startswith(p):
            response_text = response_text[len(p):].lstrip()
    if not str(response_text).strip():
        response_text = '（空の応答）'

    debug_info = data.get('debug_info')
    if isinstance(debug_info, dict) and 'history' in debug_info:
        st.session_state.server_history = debug_info.get('history')

    # store compressed memory if present
    if isinstance(data, dict) and data.get('compressed_memory'):
        st.session_state.compressed_memory = data.get('compressed_memory')

    # Append to local chat and message history
    st.session_state.local_chats.append({'created_at': data.get('created_at') or now, 'message': f'You: {message}'})
    st.session_state.local_chats.append({'created_at': data.get('created_at') or now, 'message': response_text})
    st.session_state.messages.append({"role": "user", "content": message})
    st.session_state.messages.append({"role": "assistant", "content": response_text, "debug_info": debug_info})

    return True


# ---------- AI fallback ----------
def ai_decompose(prompt: str):
    steps = []
    if not prompt: return steps
    parts = [p.strip() for p in prompt.replace('、', ',').split(',') if p.strip()]
    if len(parts) > 1:
        return [f"{i+1}. {p}" for i,p in enumerate(parts)]
    words = prompt.split()
    if len(words) <= 3: return [f"1. {prompt} を小さく試す"]
    return [f"1. {words[0]} を始める", f"2. {words[1]} を片付ける", f"3. 終わったら報告する"]


# ---------- UI components ----------
def render_header():
    st.markdown('<div class="header-container"><h1 class="header-title">Sista</h1></div>', unsafe_allow_html=True)

def render_login():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h2>ログイン / 登録</h2>', unsafe_allow_html=True)
    uname = st.text_input('ユーザー名', key='uname')
    pwd = st.text_input('パスワード', type='password', key='pwd')
    c1, c2 = st.columns(2)
    with c1:
        if st.button('ログイン'):
            login(uname, pwd)
    with c2:
        if st.button('登録'):
            register(uname, pwd)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="margin-top:.5rem;color:#666">API Base: {API_BASE}</div>', unsafe_allow_html=True)

def render_tasks_section():
    st.markdown('<div class="section-header">タスク管理</div>', unsafe_allow_html=True)
    col_left, col_right = st.columns([5,1])
    with col_left:
        new_task = st.text_input('新しいタスク', key='newtask', placeholder='やりたいことを入力...')
    with col_right:
        if st.button('更新', key='refresh_tasks'):
            st.session_state.tasks_cache = None
            # fetch now to update
            fetch_tasks()
    if st.button('タスクを追加'):
        if new_task.strip(): create_task(new_task.strip())
    tasks = fetch_tasks()
    if not tasks:
        st.markdown('<div>タスクがありません</div>', unsafe_allow_html=True)
        return
    for t in tasks:
        st.markdown('<div class="task-card">', unsafe_allow_html=True)
        cols = st.columns([5,1,1,1])
        title = t.get('title','')
        if t.get('completed'): title = f"✓ {title}"
        cols[0].write(title)
        if cols[1].button('完了', key=f'toggle-{t.get("id")}'):
            completed = t.get('completed')
            update_task(t.get('id'), {'completed': not completed})
        if cols[2].button('削除', key=f'del-{t.get("id")}'):
            delete_task(t.get('id'))
        # Execute first step for this task (calls backend /api/execute)
        if cols[3].button('最初の一歩を実行', key=f'exec-{t.get("id")}'):
            # call API
            res = api_post('/api/execute', {'task': t.get('title')})
            if res and res.status_code == 200:
                try:
                    data = res.json()
                    st.info(data.get('result') or str(data))
                except Exception:
                    st.info('実行リクエストを送信しました')
            else:
                st.warning('実行リクエストを送信できませんでした（ローカル実行を行います）')
                # fallback message
                st.info(f'『{t.get("title")}』の最初の一歩を実行しました！（ローカルモック）')
        st.markdown('</div>', unsafe_allow_html=True)

def render_chat_ai():
    st.markdown('<div class="section-header">チャット & AI分解</div>', unsafe_allow_html=True)
    # Assumes a top-level chat_input was used in main() and stored into st.session_state.chat_pending

    chat_col, ai_col = st.columns([1,1])
    with chat_col:
        st.markdown('**チャット**')
        # If there is pending input, display it and process
        if st.session_state.get('chat_pending'):
            prompt = st.session_state.pop('chat_pending')
            with st.chat_message('user'):
                st.markdown(prompt)
            with st.chat_message('assistant'):
                with st.spinner('Sistaが考えています...'):
                    ok = post_chat(prompt)
                    if ok:
                        # display latest assistant reply if present
                        for c in reversed(st.session_state.local_chats[-6:]):
                            if c.get('message') and not c.get('message').startswith('You:'):
                                st.markdown(c.get('message'))
                                break
                    else:
                        st.markdown('（送信失敗）')
        chats = fetch_chats()
        if chats:
            st.markdown('<div style="max-height:300px;overflow-y:auto">', unsafe_allow_html=True)
            for c in chats:
                st.markdown(f'<div class="chat-card">{c.get("created_at","")}: {c.get("message","")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div>チャットがありません</div>', unsafe_allow_html=True)
    with ai_col:
        st.markdown('**AI分解**')
        prompt = st.text_area('やりたいことを入力', key='ai_prompt')
        if st.button('分解する'):
            steps = ai_decompose(prompt)
            if steps:
                for s in steps: st.write(s)
                if st.button('タスクを一括作成'):
                    for s in steps:
                        create_task(s)
                    st.success('AI分解をタスクとして一括追加しました')
            else: st.warning('分解できませんでした')

def render_sidebar():
    st.markdown('### Sista設定')
    st.markdown('**LLM 設定**')
    st.session_state.developer_mode = st.checkbox('Developer Mode（思考プロセスを表示）', value=st.session_state.get('developer_mode', False))
    st.session_state.over_hallu = st.checkbox('Over-Hallucination（生出力表示）', value=st.session_state.get('over_hallu', False))
    st.session_state.user_id = st.text_input('ユーザーID', value=st.session_state.get('user_id', st.session_state.get('username', 'default_user')))
    # simple role sheet as JSON-ish key/value
    rs = st.text_input('ロールシート（tone など、簡易）', value=st.session_state.get('role_sheet', {}).get('tone', ''))
    st.session_state.role_sheet = {'tone': rs} if rs else {}
    if 'alarm_enabled' not in st.session_state: st.session_state.alarm_enabled = False
    if 'webhook_url' not in st.session_state: st.session_state.webhook_url = ''
    if 'neglect_days' not in st.session_state: st.session_state.neglect_days = 3
    st.session_state.alarm_enabled = st.checkbox('鬼電モード（アラーム）', value=st.session_state.alarm_enabled)
    st.session_state.webhook_url = st.text_input('逆ギレ時のwebhook URL', value=st.session_state.webhook_url)
    st.session_state.neglect_days = st.number_input('放置日数で逆ギレ', min_value=1, max_value=30, value=st.session_state.neglect_days)
    if st.button('鬼電シミュレート'): st.info('アラームを鳴らしました（モック）')
    if st.button('逆ギレ送信'):
        if st.session_state.webhook_url: st.info('Webhook呼び出し（モック）')
        else: st.warning('Webhook URL未設定')
    st.markdown('---')
    st.markdown(f'**API Base:** {API_BASE}')


# ---------- App entry ----------
def main():
    render_header()
    if not st.session_state.token:
        render_login()
        return
    # Top-level chat_input must be called before any columns/containers are created.
    if 'chat_pending' not in st.session_state:
        st.session_state.chat_pending = None
    user_input = st.chat_input('Sistaに話しかけてください...')
    if user_input:
        st.session_state.chat_pending = user_input
        st.session_state.local_chats.append({'created_at': __import__('datetime').datetime.now().isoformat(), 'message': f'You: {user_input}'})
    # logged-in header and logout
    cols = st.columns([4,1])
    with cols[0]: st.markdown(f'<div class="user-status">ログイン中: {st.session_state.username}</div>', unsafe_allow_html=True)
    with cols[1]:
        if st.button('ログアウト'): logout()

    # Tabs: Dashboard (tasks), Chat, AI Tools, Settings
    t1, t2, t3, t4 = st.tabs(['Dashboard', 'Chat', 'AI Tools', 'Settings'])
    with t1:
        st.markdown('## ダッシュボード')
        render_tasks_section()
    with t2:
        st.markdown('## チャット')
        render_chat_ai()
    with t3:
        st.markdown('## AI ツール')
        # reuse ai area from render_chat_ai (ai col), or provide a dedicated area
        st.markdown('AI分解と一括タスク作成')
        prompt = st.text_area('やりたいことを入力（AI分解）', key='ai_prompt_tab')
        if st.button('分解してタスク化', key='ai_decompose_tab'):
            steps = ai_decompose(prompt)
            if steps:
                for s in steps: st.write(s)
                if st.button('タスクを一括作成', key='ai_to_tasks_tab'):
                    for s in steps:
                        create_task(s)
                    st.success('AI分解をタスクとして一括追加しました')
            else:
                st.warning('分解できませんでした')
    with t4:
        st.markdown('## 設定')
        render_sidebar()


if __name__ == '__main__':
    main()
