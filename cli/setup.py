"""
Setup script for SetuPranali CLI

Install:
    pip install -e .
    
Or install from the main project:
    pip install setupranali[cli]
"""

from setuptools import setup, find_packages

setup(
    name="setupranali-cli",
    version="1.1.0",
    description="Command-line interface for SetuPranali semantic BI layer",
    author="SetuPranali Contributors",
    author_email="hello@setupranali.io",
    url="https://github.com/setupranali/setupranali.github.io",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
        "httpx>=0.25.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "setupranali=setupranali_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries",
    ],
)

