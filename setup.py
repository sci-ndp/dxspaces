from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(name='DXSpaces',
      version='0.0.5',
      description='Client library for RESTful DataSpaces',
      long_description="Placeholder - README Pending",
      long_description_content_type="text/x-rst",
      author='Philip Davis',
      author_email='philip.davis@sci.utah.edu',
      url='https://github.com/sci-ndp/dxspaces',
      install_requires=requirements,
      packages=['dxspaces'],
     )
