from setuptools import setup, find_packages

setup(
    name='heic-converter',
    version='0.1.0',
    author='jacques',
    author_email='your.email@example.com',
    description='A tool to convert HEIC images to PNG or JPG format.',
    packages=find_packages(),
    install_requires=[
        'Pillow>=9.0.0',
        'pillow-heif>=0.10.0',
        'tqdm>=4.62.0',
        'psutil>=5.9.0',
    ],
    entry_points={
        'console_scripts': [
            'heic-converter=src.main:main',
        ],
    },
)