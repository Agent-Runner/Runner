# Contributing to Agent-Runner

Thank you for your interest in contributing to Agent-Runner! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A GitHub account with a Personal Access Token (PAT) with `repo` scope

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/Agent-Runner.git
   cd Agent-Runner
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Development Workflow

### Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Type Checking

We use [MyPy](https://mypy.readthedocs.io/) for static type checking:

```bash
mypy backend/
```

### Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_agent_runner.py
```

### Pre-commit Checks

Before committing, ensure your code passes all checks:

```bash
ruff check .
ruff format --check .
mypy backend/
pytest
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-retry-logic`
- `fix/fork-timeout-issue`
- `docs/update-readme`

### Commit Messages

Follow conventional commit format:
- `feat: add retry logic for failed forks`
- `fix: handle timeout in workflow dispatch`
- `docs: update installation instructions`
- `chore: update dependencies`

### Pull Requests

1. Create a branch from `main`
2. Make your changes
3. Ensure all checks pass
4. Submit a PR with a clear description
5. Wait for review

## Project Structure

```
Agent-Runner/
├── .github/
│   └── workflows/
│       └── run.yml          # Main workflow
├── backend/
│   ├── agent_runner.py      # Core library
│   └── requirements.txt     # Dependencies
├── tests/                   # Test files
├── pyproject.toml           # Project config
├── README.md                # Documentation
└── CONTRIBUTING.md          # This file
```

## Architecture Overview

### Components

1. **GitHub Actions Workflow** (`run.yml`)
   - Clones the fork
   - Runs the OpenHands agent
   - Commits and pushes changes
   - Creates a PR
   - Sends callback notifications

2. **Backend Service** (`agent_runner.py`)
   - `AgentRunner` class: Core logic for fork management and workflow dispatch
   - `Job` dataclass: Job tracking and state management
   - FastAPI app: REST API endpoints

### Flow

```
User Request → Backend API → Fork Repo → Trigger Workflow → Agent Runs → PR Created → Callback
```

## Reporting Issues

When reporting issues, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: How to reproduce the issue
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: Python version, OS, relevant config

## Security

If you discover a security vulnerability, please do NOT open a public issue. Instead, email the maintainers directly.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Questions?

Feel free to open an issue for any questions or discussions!
