from setuptools import setup, find_packages

setup(
    name='heic-converter',
    version='0.1.0',
    author='jacques',
    author_email='your.email@example.com',
    description='A tool to convert HEIC images to PNG or JPG format.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/chambj/heic-converter',
    packages=find_packages(),
include_package_data=True,
    python_requires='>=3.7',
    install_requires=[
        'Pillow>=9.0.0',
        'pillow-heif>=0.10.0',
        'tqdm>=4.62.0',
        'psutil>=5.9.0',
    ],
    entry_points={
        'console_scripts': [
            'heic-convert=src.main:main',
        ],
    },
classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
    ],
)