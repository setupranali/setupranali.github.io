"""
SQLAlchemy dialect for SetuPranali

This package provides a SQLAlchemy dialect for connecting to SetuPranali
semantic layer, enabling integration with Apache Superset and other
SQLAlchemy-based tools.

Usage:
    from sqlalchemy import create_engine
    
    # Connect to SetuPranali
    engine = create_engine(
        "setupranali+http://localhost:8080?api_key=your-key"
    )
    
    # Or with HTTPS
    engine = create_engine(
        "setupranali+https://your-server.com?api_key=your-key"
    )

For Superset, use the SQLAlchemy URI format in the database connection:
    setupranali+http://localhost:8080?api_key=your-key
"""

from sqlalchemy_setupranali.dialect import SetuPranaliDialect
from sqlalchemy_setupranali.base import (
    SetuPranaliConnection,
    SetuPranaliCursor,
    SetuPranaliDBAPI,
)

__version__ = "1.0.0"
__all__ = [
    "SetuPranaliDialect",
    "SetuPranaliConnection",
    "SetuPranaliCursor",
    "SetuPranaliDBAPI",
]

