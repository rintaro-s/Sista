import streamlit as st
import requests
import json

# --- ページ設定 ---
st.set_page_config(
    page_title="Spunky-chan Chat",
    page_icon="R",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 定数 ---
API_URL = "http://127.0.0.1:8030/chat"

# --- サイドバー ---
with st.sidebar:
    st.title("Spunky Agent Client")
    st.write("思考拡張型LLMエージェントSpunkyとの対話クライアントです。")

    mode = st.radio(
        "表示モードを選択",
        ("User Mode", "Developer Mode"),
        help="Developer Modeでは、Spunkyの思考プロセス（デバッグ情報）を見ることができます。"
    )

    # Over-Hallucination モード切替
    over_hallu = st.checkbox(
        "Over-Hallucination（思考やタグもそのまま表示）",
        value=st.session_state.get("over_hallu", False),
        help="このモードではサーバー側の最終サニタイズをスキップし、モデルの生出力を表示します。"
    )
    st.session_state["over_hallu"] = over_hallu

    # ユーザーIDとロールシート
    user_id = st.text_input("ユーザーID", value=st.session_state.get("user_id", "default_user"))
    st.session_state["user_id"] = user_id
    st.markdown("---")
    st.subheader("ロールシート（任意）")
    rs_tone = st.text_input("tone（話し方の方針）", value=st.session_state.get("rs_tone", ""))
    st.session_state["rs_tone"] = rs_tone
    role_sheet = {"tone": rs_tone} if rs_tone else None

    if st.button("会話履歴をクリア"):
        # サーバーはステートレス。ローカルの履歴のみをクリアする
        st.session_state.messages = []
        st.session_state.server_history = []
        st.session_state.compressed_memory = None
        st.rerun()

# --- メイン画面 ---
st.title("Spunky-chan Chat")

# --- チャット履歴の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "server_history" not in st.session_state:
    st.session_state.server_history = []
if "compressed_memory" not in st.session_state:
    st.session_state.compressed_memory = None

# --- チャット履歴の表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # デベロッパーモードの場合、デバッグ情報を表示
        if st.session_state.get("developer_mode", None) is None:
            st.session_state["developer_mode"] = mode
        if mode == "Developer Mode" and "debug_info" in message and message["debug_info"]:
            with st.expander("思考プロセスを見る"):
                dbg = message["debug_info"]
                try:
                    st.json(dbg)
                except Exception:
                    st.write(dbg)
                prompts = dbg.get("prompts") if isinstance(dbg, dict) else None
                history = dbg.get("history") if isinstance(dbg, dict) else None
                if isinstance(prompts, dict):
                    st.markdown("### prompts.reason")
                    try:
                        st.code(json.dumps(prompts.get("reason", {}), ensure_ascii=False, indent=2), language="json")
                    except Exception:
                        st.write(prompts.get("reason"))
                    st.markdown("### prompts.render")
                    try:
                        st.code(json.dumps(prompts.get("render", {}), ensure_ascii=False, indent=2), language="json")
                    except Exception:
                        st.write(prompts.get("render"))
                if isinstance(history, (list, dict)):
                    st.markdown("### server history (latest)")
                    try:
                        st.json(history)
                    except Exception:
                        st.write(history)

# --- ユーザーからの入力を受け付け --- 
if prompt := st.chat_input("Spunkyに話しかけてね！"):
    # ユーザーのメッセージを履歴に追加して表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Spunkyからの応答を待つ間、スピナーを表示
    with st.chat_message("assistant"):
        with st.spinner("Spunkyが考えています..."):
            try:
                # APIサーバーにリクエストを送信
                # 送信用に、現在までの履歴を user/assistant のみ抽出
                history_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages if m.get("role") in ("user", "assistant")
                ]

                payload = {
                    "user_id": st.session_state.get("user_id", "default_user"),
                    "text": prompt,
                    "role_sheet": role_sheet,
                    "over_hallucination": st.session_state.get("over_hallu", False),
                    "history": history_messages,
                    "compressed_memory": st.session_state.get("compressed_memory"),
                }
                resp = requests.post(API_URL, json=payload)
                resp.raise_for_status()
                try:
                    data = resp.json()
                except ValueError:
                    data = {"response": resp.text}

                response_text = data.get("response", "エラー：予期せぬ応答形式です。")
                # 先頭の接頭辞を除去
                for p in ("答え:", "回答:", "Answer:", "answer:"):
                    if isinstance(response_text, str) and response_text.startswith(p):
                        response_text = response_text[len(p):].lstrip()
                if not str(response_text).strip():
                    response_text = "（空の応答）"

                debug_info = data.get("debug_info")
                if isinstance(debug_info, dict) and "history" in debug_info:
                    st.session_state.server_history = debug_info["history"]

                # 返ってきた圧縮履歴を保存
                if isinstance(data, dict) and data.get("compressed_memory"):
                    st.session_state.compressed_memory = data.get("compressed_memory")

                # 応答を表示
                st.markdown(response_text)

                # 応答を履歴に追加（デバッグ情報も含む）
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "debug_info": debug_info,
                })

            except requests.exceptions.RequestException as e:
                error_message = f"ごめんね、サーバーに接続できなかったみたい… ({e})"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})