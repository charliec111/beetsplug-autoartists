from distutils.core import setup

iday = datetime.date.today().strftime("%Y.%-m.%-d")
setup(
    name="autoartists",
    version="0.1",
    packages=["beetsplug"],
    license="MIT",
    long_description=open("README.txt").read(),
)
