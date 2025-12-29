"""
SQLAlchemy dialect for SetuPranali - Apache Superset compatible
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sqlalchemy-setupranali",
    version="1.0.0",
    author="SetuPranali Community",
    author_email="community@setupranali.io",
    description="SQLAlchemy dialect for SetuPranali semantic layer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/setupranali/setupranali.github.io",
    project_urls={
        "Documentation": "https://setupranali.github.io/integrations/bi-tools/superset/",
        "Bug Tracker": "https://github.com/setupranali/setupranali.github.io/issues",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Database :: Front-Ends",
    ],
    python_requires=">=3.8",
    install_requires=[
        "sqlalchemy>=1.4.0",
        "requests>=2.25.0",
    ],
    extras_require={
        "superset": ["apache-superset>=2.0.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "sqlalchemy.dialects": [
            "setupranali = sqlalchemy_setupranali.dialect:SetuPranaliDialect",
            "setupranali.http = sqlalchemy_setupranali.dialect:SetuPranaliDialect",
            "setupranali.https = sqlalchemy_setupranali.dialect:SetuPranaliDialect",
        ],
    },
    keywords=[
        "sqlalchemy",
        "dialect",
        "setupranali",
        "superset",
        "semantic-layer",
        "bi",
        "analytics",
    ],
)

