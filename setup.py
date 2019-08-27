from setuptools import setup

requirements = []
with open('requirements.txt') as f:
  requirements = f.read().splitlines()

setup(name="NeonBot", version="1.0.0", author="NeonSpectrum", description="A Discord Bot made using discord.py")
