import os
import requests
import json

def try_payload(url, payload, timeout=20):
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        try:
            body = r.json()
        except Exception:
            body = r.text
        print('URL:', url)
        print('STATUS:', r.status_code)
        print('PAYLOAD:', json.dumps(payload)[:1000])
        print('BODY:', json.dumps(body)[:2000] if not isinstance(body, str) else body[:2000])
        print('---')
        return True
    except Exception as e:
        print('URL:', url)
        print('EXCEPTION:', type(e).__name__, str(e))
        print('PAYLOAD:', json.dumps(payload)[:1000])
        print('---')
        return False


def main():
    url = os.environ.get('LMSTUDIO_URL')
    if not url:
        print('LMSTUDIO_URL not set in environment')
        return

    text = 'ping from tmp_test_llm'

    # OpenAI-style chat payload
    openai_payload = {
        'model': os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
        'messages': [{'role': 'user', 'content': text}],
        'temperature': float(os.environ.get('OPENAI_TEMPERATURE', '0.7')),
    }

    # other common shapes
    payloads = [
        openai_payload,
        {'input': text, 'history': []},
        {'prompt': text},
        {'text': text},
        {'messages': [{'role': 'user', 'content': text}]},
    ]

    # candidate endpoints to try (if url is a base, try common suffixes)
    candidates = [url]
    if url.endswith('/'):
        base = url.rstrip('/')
    else:
        base = url
    candidates.extend([
        base,
        base + '/predict',
        base + '/api/predict',
        base + '/v1/generate',
        base + '/generate',
        base + '/v1/chat/completions',
    ])

    # try each combination once
    for c in candidates:
        for p in payloads:
            ok = try_payload(c, p)
            if ok:
                # if we got status 200/201 and body printed, continue trying to find best
                pass


if __name__ == '__main__':
    main()
