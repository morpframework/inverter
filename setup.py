from setuptools import setup, find_packages
import sys, os

version = '0.1.1'

def readfile(name):
    with open(os.path.join(os.path.dirname(__file__), name)) as f:
        out = f.read()
    return out

desc = '\n'.join([readfile('README.rst'), readfile('CHANGELOG.rst')])

setup(name='inverter',
      version=version,
      description="Convert dataclass to another class",
      long_description=desc,
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
      ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='dataclass converter',
      author='Izhar Firdaus',
      author_email='kagesenshi.87@gmail.com',
      url='http://github.com/morpframework/inverter/',
      license='Apache-2.0',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'colander',
          'jsl',
          'sqlalchemy',
          'sqlalchemy_utils',
          'sqlalchemy_jsonfield',
          'deform',
          'pytz',
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
