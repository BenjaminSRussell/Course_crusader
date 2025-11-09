"""
Setup configuration for Course Crusader.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="coursecrusader",
    version="0.1.0",
    author="Course Crusader Team",
    description="Unified course catalog scraper for multiple universities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BenjaminSRussell/Course_crusader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Topic :: Education",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "scrapy>=2.11.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "PyPDF2>=3.0.0",
        "pypdf>=3.17.0",
        "pdfplumber>=0.10.0",
        "jsonschema>=4.20.0",
        "click>=8.1.0",
        "rich>=13.7.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "coursecrusader=coursecrusader.cli:main",
        ],
    },
)
