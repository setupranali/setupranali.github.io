"""
SetuPranali Python SDK Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="setupranali",
    version="1.0.0",
    author="SetuPranali Contributors",
    author_email="hello@setupranali.io",
    description="Python SDK for SetuPranali semantic analytics layer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/setupranali/setupranali.github.io",
    project_urls={
        "Documentation": "https://setupranali.github.io",
        "Bug Tracker": "https://github.com/setupranali/setupranali.github.io/issues",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "async": ["httpx>=0.25.0"],
        "pandas": ["pandas>=1.5.0"],
        "all": ["httpx>=0.25.0", "pandas>=1.5.0"],
    },
    keywords="analytics, bi, business-intelligence, semantic-layer, data",
)

