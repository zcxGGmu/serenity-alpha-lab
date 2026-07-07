from setuptools import find_packages, setup


setup(
    name="serenity-alpha-lab",
    version="0.1.0",
    description="Local-first Serenity-style supply-chain bottleneck research engine",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={
        "console_scripts": [
            "serenity-alpha-lab=serenity_alpha_lab.cli:main",
        ],
    },
    python_requires=">=3.9",
)
