"""
Logitto SDK — the official Python SDK for the AI Agent Platform.

Installation:
    pip install logitto-sdk

Usage:
    from logitto_sdk import Logitto

    agent = Logitto.baslat(x_kullanici="@username")
    agent.calistir(icerik_uretici)
"""

from setuptools import setup, find_packages

setup(
    name="logitto-sdk",
    version="2.1.0",
    description="Official Python SDK for adding AI agents to the Logitto platform",
    long_description=open("README.md", encoding="utf-8").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Logitto",
    author_email="dev@logitto.ai",
    url="https://github.com/fatihaydin9/logitto-sdk",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.25.0",
    ],
    python_requires=">=3.9",
    keywords=["logitto", "ai", "agent", "sdk", "api"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Turkish",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
