import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Config
# Default to backend host port 8030 per user request. Can be overridden with API_BASE env var.
API_BASE = os.getenv('API_BASE', 'http://localhost:8030')
# 最大待機時間（秒）。環境変数で上書きできます。
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '120'))
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
        # DEBUG: surface response status and body when in developer_mode for diagnosis
        if st.session_state.get('developer_mode'):
            try:
                st.write({'request_url': API_CHAT, 'payload': payload})
                st.write({'status_code': resp.status_code, 'response_text': resp.text})
            except Exception:
                pass
    except Exception as e:
        # Network error: fallback: サーバーが落ちている場合はエラーのみ返す
        st.warning(f"LLMサーバーに接続できませんでした: {e}")
        reply = '（サーバーに接続できませんでした）'
        st.session_state.local_chats.append({'created_at': now, 'message': f'You: {message}'})
        st.session_state.local_chats.append({'created_at': now, 'message': reply})
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


def render_ai_todos_dashboard():
    """Fetch AI-generated ToDos from backend and render them in order with simple controls."""
    st.markdown('<div class="section-header">AI分解 (JSON ToDo ダッシュボード)</div>', unsafe_allow_html=True)
    prompt = st.text_input('AI分解したい内容', key='ai_todos_prompt')
    cols = st.columns([3,1])
    with cols[1]:
        if st.button('取得', key='fetch_ai_todos'):
            if not prompt.strip():
                st.warning('プロンプトを入力してください')
            else:
                try:
                    r = requests.post(f"{API_BASE}/ai/todos", json={"prompt": prompt}, headers=_auth_headers(), timeout=API_TIMEOUT)
                except Exception as e:
                    # capture the exception in the UI
                    st.error(f"ネットワークエラー: {e}")
                    r = None
                if not r:
                    st.warning('バックエンドに接続できません')
                elif r.status_code != 200:
                    # If the request timed out on the server side, guide the user to retry
                    if 'Read timed out' in getattr(r, 'text', ''):
                        st.info(f'サーバーで処理中のため応答に時間がかかっています（{API_TIMEOUT}s）。再度「取得」を押してみてください。')
                    st.error(f'エラー: {r.status_code} {r.text}')
                else:
                    try:
                        data = r.json()
                        st.session_state.ai_todos = data.get('todos', [])
                        st.session_state.ai_todos_index = 0
                    except Exception:
                        st.error('不正なレスポンス')

    # Initialize session state for todos
    if 'ai_todos' not in st.session_state:
        st.session_state.ai_todos = []
    if 'ai_todos_index' not in st.session_state:
        st.session_state.ai_todos_index = 0

    todos = st.session_state.ai_todos
    idx = st.session_state.ai_todos_index

    if not todos:
        st.markdown('<div>AIで分解されたタスクが未取得です。上の「取得」を押してください。</div>', unsafe_allow_html=True)
        return

    # Display current todo in order
    st.markdown(f'**進行中のタスク ({idx+1}/{len(todos)})**')
    current = todos[idx]
    st.markdown(f"- ID: {current.get('id')}  \n- タイトル: {current.get('title')}  \n- ステータス: {current.get('status')}")

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button('完了にする', key=f'complete_ai_{idx}'):
            todos[idx]['status'] = 'done'
            st.session_state.ai_todos = todos
            st.experimental_rerun()
    with c2:
        if st.button('次へ', key=f'next_ai_{idx}'):
            if idx + 1 < len(todos):
                st.session_state.ai_todos_index = idx + 1
            else:
                st.success('すべてのタスクを表示しました')
            st.experimental_rerun()
    with c3:
        if st.button('タスクを作成', key=f'create_ai_{idx}'):
            # call create_task to add to tasks list (will fallback locally if unauthorized)
            create_task(current.get('title'))
            st.success('タスク作成リクエストを送信しました')

    # Show list of remaining tasks
    st.markdown('### 残りのタスク')
    for i, t in enumerate(todos):
        status = t.get('status', 'pending')
        prefix = '✓ ' if status == 'done' else ''
        st.write(f"{i+1}. {prefix}{t.get('title')}")

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
        # AI 分解 UI を削除しました。AI 分解は「AI ツール」タブに統合されています。
        st.markdown('<div>AI分解は「AI ツール」タブで利用できます。</div>', unsafe_allow_html=True)

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
        render_ai_todos_dashboard()
    with t2:
        st.markdown('## チャット')
        render_chat_ai()
    with t3:
        st.markdown('## AI ツール')
        st.markdown('AI分解と一括タスク作成')
        prompt = st.text_area('やりたいことを入力（AI分解）', key='ai_prompt_tab')
        if st.button('分解してタスク化', key='ai_decompose_tab'):
            todos = None
            server_response = None
            r = None
            r_json = None
            error_detail = None
            try:
                r = requests.post(f"{API_BASE}/ai/todos", json={"prompt": prompt}, headers=_auth_headers(), timeout=API_TIMEOUT)
                server_response = r
                if r.status_code == 200:
                    try:
                        r_json = r.json()
                        todos = r_json.get('todos', [])
                    except Exception as e:
                        error_detail = f"JSON decode error: {e}"
                else:
                    error_detail = f"Status: {r.status_code}, Body: {r.text}"
            except Exception as e:
                error_detail = f"Request error: {e}"

            with st.expander('AI分解APIレスポンス詳細', expanded=True):
                st.write({
                    'status_code': getattr(r, 'status_code', None),
                    'body': getattr(r, 'text', None),
                    'json': r_json,
                    'error_detail': error_detail
                })

            # Detect server-side LLM errors returned in debug
            llm_error_msg = None
            if r_json and isinstance(r_json, dict):
                try:
                    llm_error_msg = r_json.get('debug', {}).get('llm_error')
                except Exception:
                    llm_error_msg = None

            if not todos:
                # タイムアウト系のメッセージがあれば処理中の可能性があるので、再試行を促す
                if error_detail and 'Read timed out' in str(error_detail):
                    st.info(f'サーバーで処理中のため応答に時間がかかっています（{API_TIMEOUT}s）。処理が完了している場合は、もう一度「分解してタスク化」を押して結果を取得してください。')
                    return
                # choices[0].message.content から箇条書きや番号リストを抽出してタスク化
                content = None
                if r_json and isinstance(r_json, dict):
                    # OpenAI互換形式
                    try:
                        content = r_json.get('choices', [{}])[0].get('message', {}).get('content', None)
                    except Exception:
                        content = None
                tasks_from_content = []
                if content:
                    import re
                    # 箇条書きや番号リストを抽出
                    lines = content.splitlines()
                    for line in lines:
                        m = re.match(r"^\s*([0-9]+\.|・|\-|\*)\s*(.+)$", line)
                        if m:
                            tasks_from_content.append(m.group(2).strip())
                    # 箇条書きが1つもなければ、content全体を1タスクとして扱う
                    if not tasks_from_content and content.strip():
                        tasks_from_content = [content.strip()]
                if tasks_from_content:
                    todos = [{ 'id': i+1, 'title': t, 'status': 'pending', 'order': i+1 } for i, t in enumerate(tasks_from_content)]
            if not todos:
                st.error('AI分解API（LMstudio）から分解結果を取得できませんでした。サーバーが起動しているか、レスポンス形式を確認してください。')
                return
            # If the backend reports an LLM-level error (e.g. LMStudio couldn't reach the model),
            # do NOT auto-create tasks unless the user explicitly forces creation.
            if llm_error_msg:
                with st.expander('バックエンドのLLM接続エラー詳細（処理を中断しました）', expanded=True):
                    st.error(llm_error_msg)
                    st.write('バックエンドは一時的にLLMへ接続できなかったため、出力は信頼できない可能性があります。自動でタスク化は行いません。')
                force = st.checkbox('LLM接続エラーを無視して、分解された内容をタスク化する', key='force_create_ai_todos')
                if not force:
                    st.warning('タスク作成は保留されました。問題を確認してから再度お試しください。')
                    return
                else:
                    st.info('LLM接続エラーを無視して、ユーザーの許可でタスクを作成します')

            else:
                st.markdown('### 分解結果')
                with st.expander('分解結果（展開）', expanded=True):
                    st.markdown('<div style="max-height:220px;overflow-y:auto;padding:6px;border:1px solid #eee;border-radius:6px">', unsafe_allow_html=True)
                    for i, t in enumerate(todos):
                        st.write(f"{i+1}. {t.get('title')}")
                    st.markdown('</div>', unsafe_allow_html=True)

                # Create tasks on server and show concise result
                created = []
                for t in todos:
                    title = t.get('title')
                    payload = {'title': title}
                    url = f"{API_BASE}/tasks"
                    try:
                        resp = requests.post(url, json=payload, headers=_auth_headers(), timeout=5)
                        success = resp.status_code in (200,201)
                        created.append({'title': title, 'ok': success, 'status_code': resp.status_code if hasattr(resp, 'status_code') else None})
                    except Exception as e:
                        created.append({'title': title, 'ok': False, 'error': str(e)})

                # Show concise summary inside an expander
                with st.expander('作成結果（簡潔表示）', expanded=True):
                    for c in created:
                        if c.get('ok'):
                            st.success(f"作成成功: {c.get('title')}")
                        else:
                            st.error(f"作成失敗: {c.get('title')} - {c.get('error', c.get('status_code'))}")

                # 分解したタスクをダッシュボードのタスク一覧に自動で反映
                st.session_state.tasks_cache = None
                fetch_tasks()
                st.success('分解したタスクをダッシュボードに追加しました')
    with t4:
        st.markdown('## 設定')
        render_sidebar()


if __name__ == '__main__':
    main()
