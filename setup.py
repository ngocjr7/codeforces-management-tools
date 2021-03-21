from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

PROJECT_URLS = {
    'Bug Tracker': 'https://github.com/ngocjr7/codeforces-management-tools/issues',
    'Documentation': 'https://github.com/ngocjr7/codeforces-management-tools/blob/master/README.md',
    'Source Code': 'https://github.com/ngocjr7/codeforces-management-tools'
}

setup(name='conmato',
      description='A Command Line Interface for Codeforces Management Tools',
      author='Ngoc Bui',
      long_description=long_description,
      long_description_content_type="text/markdown",
      project_urls=PROJECT_URLS,
      author_email='ngocjr7@gmail.com',
      version='0.0.2',
      entry_points='''
        [console_scripts]
        conmato=conmato.cli:cli
      ''',
      packages=find_packages(),
      python_requires='>=3.6')

