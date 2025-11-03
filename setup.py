"""Setup configuration for HIVE project."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="hive-mcp",
    version="0.1.0",
    author="Hjalmar",
    description="HIVE MCP Agent - Enables Claude instances to join the HIVE network",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "mcp>=1.0.0",
        "httpx>=0.25.2",
        "pydantic>=2.5.0",
    ],
    extras_require={
        "server": [
            "fastapi>=0.104.1",
            "uvicorn[standard]>=0.24.0",
            "redis>=5.0.1",
            "aiosqlite>=0.19.0",
            "async-upnp-client>=0.36.2",
            "python-multipart>=0.0.6",
            "pyyaml>=6.0.1",
        ],
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "hive-mcp=mcp.server:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
