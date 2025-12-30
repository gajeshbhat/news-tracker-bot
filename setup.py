"""
Setup script for News Tracker Bot
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="news-tracker-bot",
    version="2.0.0",
    author="Gajesh Bhat",
    description="A Telegram bot for personalized news summaries with audio support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "pymongo>=4.0.0",
        "python-telegram-bot[job-queue]>=20.0",
        "gtts>=2.2.0",
        "pyttsx3>=2.90",
        "edge-tts>=6.0.0",
        "click>=8.0.0",
        "tabulate>=0.9.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.18.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "news-tracker-bot=news_tracker.cli.commands:cli",
            "ntb=news_tracker.cli.commands:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "news_tracker": ["*.md", "*.txt"],
    },
)
