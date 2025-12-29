# Contributing to SetuPranali

First off, thank you for considering contributing to SetuPranali! 🎉

This project is built by the community, for the community. Every contribution matters—whether it's fixing a typo, adding a database adapter, or improving documentation.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Quick Start](#quick-start)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Community](#community)
- [Recognition](#recognition)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to conduct@setupranali.io.

## Quick Start

```bash
# Fork, clone, and set up in 2 minutes
git clone https://github.com/YOUR_USERNAME/connector.git
cd connector
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest  # Run tests
```

Then make changes, commit, and open a PR!

## Getting Started

### Issues

- **Bug Reports**: If you find a bug, please create an issue with a clear description, steps to reproduce, and expected vs actual behavior.
- **Feature Requests**: We love new ideas! Open an issue describing the feature and why it would be valuable.
- **Questions**: Use GitHub Discussions for questions about usage or architecture.

### Good First Issues

Look for issues labeled `good first issue` - these are specifically curated for newcomers:

- Documentation improvements
- Adding tests
- Small bug fixes
- New database adapter implementations

## How Can I Contribute?

### 1. Database Adapters

We're always looking to support more databases! Current priorities:

- [ ] Trino/Presto
- [ ] Apache Druid
- [ ] TimescaleDB
- [ ] CockroachDB
- [ ] SQLite
- [ ] Oracle
- [ ] SQL Server

See `app/adapters/base.py` for the adapter interface.

### 2. BI Tool Integrations

- Improve existing connectors (Power BI OData, Tableau WDC)
- Add new connectors (Metabase, Superset, Looker Studio)
- Better authentication methods

### 3. Documentation

- Tutorials and guides
- Video walkthroughs
- Translation to other languages
- Architecture deep-dives

### 4. Testing

- Unit tests for adapters
- Integration tests
- Performance benchmarks
- Load testing

### 5. Core Features

- Query optimization
- Caching improvements
- Security enhancements
- Monitoring and observability

## Development Setup

### Prerequisites

- Python 3.9+
- Redis (for caching)
- Docker (optional, for testing databases)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/setupranali/setupranali.github.io.git
cd setupranali

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Copy environment file
cp env.example .env

# Generate secret key
python -c "from cryptography.fernet import Fernet; print(f'UBI_SECRET_KEY={Fernet.generate_key().decode()}')"

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_adapters.py

# Specific test
pytest tests/test_adapters.py::test_duckdb_adapter
```

### Building Documentation

```bash
# Install docs dependencies
pip install -r requirements-docs.txt

# Serve locally
cd ubi-connector
mkdocs serve

# Build static site
mkdocs build
```

## Pull Request Process

### 1. Before You Start

- Check existing issues and PRs to avoid duplicates
- For large changes, open an issue first to discuss
- Fork the repository and create a branch from `main`

### 2. Branch Naming

```
feature/add-trino-adapter
fix/odata-date-handling
docs/kubernetes-guide
test/adapter-integration-tests
```

### 3. Making Changes

- Write clear, concise commit messages
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass locally

### 4. Submitting

1. Push your branch to your fork
2. Open a Pull Request against `main`
3. Fill out the PR template completely
4. Link any related issues

### 5. Review Process

- Maintainers will review within 3-5 business days
- Address feedback promptly
- Once approved, a maintainer will merge

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] No breaking changes (or clearly documented)

## Style Guidelines

### Python

We follow [PEP 8](https://pep8.org/) with these specifics:

```python
# Use type hints
def execute_query(self, sql: str, params: dict | None = None) -> list[dict]:
    ...

# Docstrings for public methods
def get_adapter(source_type: str) -> BaseAdapter:
    """
    Get an adapter instance for the given source type.
    
    Args:
        source_type: Database type (e.g., 'postgresql', 'snowflake')
        
    Returns:
        Configured adapter instance
        
    Raises:
        ValueError: If source_type is not supported
    """
    ...

# Use descriptive variable names
connection_pool = create_pool(...)  # Good
cp = create_pool(...)               # Avoid
```

### Formatting

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type checking
mypy app/
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Trino database adapter
fix: handle null values in OData responses
docs: add Kubernetes deployment guide
test: add integration tests for BigQuery adapter
refactor: simplify query builder logic
chore: update dependencies
```

## Community

### Getting Help

- **GitHub Discussions**: For questions and general discussion
- **Discord**: [Join our Discord](https://discord.gg/setupranali) for real-time chat
- **Stack Overflow**: Tag questions with `setupranali`

### Stay Updated

- Watch the repository for updates
- Follow our [blog](https://blog.setupranali.dev) for announcements
- Subscribe to release notifications

### Recognition

Contributors are recognized in:

- The project README
- Release notes
- Our documentation

### Maintainers

Questions about contributing? Reach out to:

- [@maintainer1](https://github.com/maintainer1)
- [@maintainer2](https://github.com/maintainer2)

---

## Recognition

We believe in celebrating our contributors!

### How We Recognize You

- 🏆 **Contributors list** — All contributors listed in the repository
- 📝 **Release notes** — Mentioned for significant contributions
- 🎁 **Swag** — Stickers and t-shirts for major contributors
- ⭐ **Maintainer status** — For sustained, high-quality contributions

### Becoming a Maintainer

Maintainers are community members who have demonstrated:

1. Consistent, quality contributions over time
2. Helping others in Issues, Discussions, or Discord
3. Understanding of project goals and values
4. Good judgment in code review

Interested? Keep contributing, and we'll reach out!

---

## Thank You! 🙏

Every contribution matters, whether it's:

- 🐛 Fixing a typo in docs
- 🔍 Reporting a bug
- 💡 Suggesting a feature
- 💻 Writing code
- 🤝 Helping others

**You are what makes open source great. Thank you for being part of this community!**

---

<p align="center">
  <strong>Questions?</strong> Ask in <a href="https://discord.gg/setupranali">Discord</a> or <a href="https://github.com/setupranali/setupranali.github.io/discussions">GitHub Discussions</a>
</p>

