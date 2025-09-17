import os
import requests
from typing import Optional, Any, Dict, List


def call_llm(
    text: str,
    history: Optional[List[Dict[str, Any]]] = None,
    role_sheet: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    over_hallucination: bool = False,
    compressed_memory: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Centralized LLM call. Tries LMStudio (local) first if LMSTUDIO_URL is set, otherwise falls back to OpenAI if OPENAI_API_KEY is present.
    Returns a normalized dict with keys: response (str), debug_info (dict), compressed_memory (optional)
    """
    LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL")
    OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

    # Helper to build LMStudio payload
    def _build_lm_payload():
        payload = {
            "input": text,
            "history": history,
            "role_sheet": role_sheet,
            "over_hallucination": over_hallucination,
            "compressed_memory": compressed_memory,
        }
        if user_id is not None:
            try:
                payload_user = int(user_id)
                payload["user_id"] = payload_user
            except Exception:
                # omit non-int user ids
                pass
        return payload

    # Try LMStudio/local LLM first
    if LMSTUDIO_URL:
        # If user provided a full OpenAI-style path, prefer OpenAI-style payload (model/messages)
        def _openai_payload():
            model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
            messages = []
            if role_sheet and isinstance(role_sheet, dict):
                tone = role_sheet.get("tone")
                if tone:
                    messages.append({"role": "system", "content": f"You are an assistant. Tone: {tone}"})
            if history and isinstance(history, list):
                for h in history:
                    role = h.get("role") if isinstance(h, dict) else "user"
                    content = h.get("content") if isinstance(h, dict) else str(h)
                    messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": text})
            payload = {"model": model, "messages": messages, "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))}
            return payload

        # Build candidate endpoints: prefer exact LMSTUDIO_URL; if it doesn't look like a chat/completions path, try adding it
        candidate_paths = [LMSTUDIO_URL]
        if not LMSTUDIO_URL.rstrip('/').endswith('/v1/chat/completions'):
            candidate_paths.append(LMSTUDIO_URL.rstrip('/') + '/v1/chat/completions')

        # First try OpenAI-style payloads (many modern proxies accept this)
        last_exc = None
        openai_payload = _openai_payload()
        for path in candidate_paths:
            try:
                r = requests.post(path, json=openai_payload, timeout=timeout)
                if r.status_code in (200, 201):
                    try:
                        data = r.json()
                    except Exception:
                        data = r.text
                    # extract assistant content for chat completions
                    assistant_text = ''
                    if isinstance(data, dict):
                        try:
                            assistant_text = data.get('choices', [])[0].get('message', {}).get('content', '')
                        except Exception:
                            assistant_text = ''
                        # fallback: common fields
                        if not assistant_text:
                            for k in ("response", "text", "output", "result", "generated_text", "generation"):
                                if k in data and data[k]:
                                    assistant_text = data[k]
                                    break
                    else:
                        assistant_text = str(data)
                    return {"response": assistant_text, "debug_info": {"lm_raw": data, "endpoint": path, "payload_used": openai_payload}, "compressed_memory": None}
                else:
                    last_exc = (path, r.status_code, r.text)
            except requests.exceptions.RequestException as e:
                last_exc = (path, str(e))
                continue

        # If OpenAI-style attempts failed, fall back to simpler shapes (input/text/messages)
        payload_shapes = []
        payload_shapes.append(_build_lm_payload())
        payload_shapes.append({"prompt": text})
        payload_shapes.append({"input": text})
        payload_shapes.append({"text": text})
        payload_shapes.append({"messages": [{"role": "user", "content": text}]})

        for path in candidate_paths:
            for payload in payload_shapes:
                try:
                    r = requests.post(path, json=payload, timeout=timeout)
                    if r.status_code not in (200, 201):
                        last_exc = (path, r.status_code, r.text)
                        continue
                    try:
                        data = r.json()
                    except Exception:
                        data = r.text
                    assistant_text = ''
                    if isinstance(data, dict):
                        for k in ("response", "text", "output", "result", "generated_text", "generation"):
                            if k in data and data[k]:
                                assistant_text = data[k]
                                break
                        if not assistant_text and 'results' in data and isinstance(data['results'], list) and data['results']:
                            first = data['results'][0]
                            if isinstance(first, dict):
                                assistant_text = first.get('content') or first.get('text') or str(first)
                            else:
                                assistant_text = str(first)
                    else:
                        assistant_text = str(data)
                    return {"response": assistant_text, "debug_info": {"lm_raw": data, "endpoint": path, "payload_used": payload}, "compressed_memory": None}
                except requests.exceptions.RequestException as e:
                    last_exc = (path, str(e))
                    continue

        return {"error": f"LMStudio request attempts failed. Last: {last_exc}"}

    # Fallback to OpenAI
    if OPENAI_KEY:
        try:
            model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
            messages = []
            if role_sheet and isinstance(role_sheet, dict):
                tone = role_sheet.get("tone")
                if tone:
                    messages.append({"role": "system", "content": f"You are an assistant. Tone: {tone}"})
            if history and isinstance(history, list):
                for h in history:
                    role = h.get("role") if isinstance(h, dict) else "user"
                    content = h.get("content") if isinstance(h, dict) else str(h)
                    messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": text})

            payload = {"model": model, "messages": messages, "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))}
            headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
            r = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            assistant_text = ""
            try:
                assistant_text = data.get("choices", [])[0].get("message", {}).get("content", "")
            except Exception:
                assistant_text = str(data.get("choices", [0]))
            debug_info = {"openai": {"usage": data.get("usage")}}
            return {"response": assistant_text, "debug_info": debug_info, "compressed_memory": None}
        except requests.exceptions.RequestException as e:
            return {"error": f"OpenAI request failed: {e}"}

    return {"error": "No LLM configured. Set LMSTUDIO_URL or OPENAI_API_KEY on the server."}
