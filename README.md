# Brain Jelly

Brain Jelly is a Flask-based backend scaffold designed to serve as the foundation for future APIs, background tasks, and service integrations. This initial structure follows the application factory pattern and leaves space for services, models, and Celery tasks.

## Project Structure

```
backend/
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── tasks/
├── config.py
├── requirements.txt
└── .env.example
```

## Getting Started

1. **Install Python 3.11+** (recommended via [pyenv](https://github.com/pyenv/pyenv)).
2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```
4. **Configure environment variables**
   ```bash
   cp backend/.env.example backend/.env
   ```
5. **Run the development server**
   ```bash
   export FLASK_APP=backend.app
   flask run --debug
   ```

## Next Steps

- Implement database models in `backend/app/models`.
- Add API routes and blueprints inside `backend/app/routes`.
- Configure Celery workers and tasks in `backend/app/tasks`.
- Document service logic in `backend/app/services`.

