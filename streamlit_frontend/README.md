Streamlit frontend for Sista

Quick start

1. Install dependencies (preferably in a virtualenv):

```bash
pip install -r streamlit_frontend/requirements.txt
```

2. Run the Streamlit app:

```bash
streamlit run streamlit_frontend/app.py
```

3. The app expects the backend API at http://localhost:8030. If your backend runs elsewhere, set the `API_BASE` environment variable.

Features

- Register / Login (JWT)
- List tasks
- Create task
- Toggle complete / Delete task

Notes

- This is a minimal, unstyled UI intended for quick local testing.
- For production, secure storage of tokens and HTTPS are required.
