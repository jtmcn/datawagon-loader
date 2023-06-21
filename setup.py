from setuptools import setup, find_packages

setup(
    name="datawagon",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "psycopg2-binary",
        "python-dotenv",
        "pandas",
        "sqlalchemy"
    ],
    entry_points={
        "console_scripts": [
            "datawagon = datawagon.main:cli",
        ],
    },
    author="Joel M",
    author_email="jtmcn.dev@gmail.com",
    description="A command-line tool for loading compressed CSV files into a PostgreSQL database.",
    license="MIT",
    keywords="csv database postgresql",
)
