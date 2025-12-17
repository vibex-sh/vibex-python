"""
Setup configuration for Vibex Python SDK
"""

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='vibex_sh',
    version='0.10.0',
    description='vibex.sh Python SDK - Fail-safe logging handler for vibex.sh',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='vibex.sh',
    author_email='support@vibex.sh',
    url='https://github.com/vibex-sh/vibex-python',
    packages=find_packages(),
    install_requires=[
        'requests>=2.28.0',
    ],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Logging',
    ],
)

