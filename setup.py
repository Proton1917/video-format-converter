from setuptools import setup, find_packages

setup(
    name="video-converter",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["serve_app"],
    install_requires=[
        "tqdm>=4.64.0",
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.22.0",
        "python-multipart>=0.0.6",
    ],
    entry_points={
        'console_scripts': [
            'video-converter=video_converter.__main__:main',
            'video-converter-serve=serve_app:main',
        ],
    },
    include_package_data=True,
    package_data={
        "video_converter": ["resources/*.html"],
    },
    author="Gordon Gauer",
    author_email="proton@gmail.com",
    description="视频格式转换工具，提供命令行操作与HTML界面模板",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Proton1917/video-format-converter",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Multimedia :: Video :: Conversion",
    ],
    python_requires=">=3.7",
)
