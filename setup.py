from setuptools import setup, find_packages

setup(
    name="linpdf",
    version="0.1.0",
    description="A Linux-native PDF editor inspired by Foxit PDF Editor",
    author="LinPDF",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PySide6>=6.6.0",
        "PyMuPDF>=1.23.0",
        "Pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "linpdf=main:main",
        ],
    },
    python_requires=">=3.9",
)
