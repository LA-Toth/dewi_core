DEWI core: An application framework
===================================

Name
----
DEWI: Old Welsh form of David

The name is chosen because of the similarity to DWA, which was the project's
original name, which stands for Developer's Work Area.


Purpose
-------

This code is the core part of DEWI_.

.. _DEWI: https://github.com/LA-Toth/dewi

The plugins ensure load codes dynamically, without loading everything.
An application implementation is also added in ``MainApplication`` class.

Installation
------------

It can be installed from source::

        python3 setup.py

Or from pip::

        pip install dewi_core


Usage as a plugin framework
---------------------------

A minimal example can be found in the ``samples/as_framework`` directory,
the application is named as Steven.

Assuming that it's already created, it can be the aforementioned way::

        dewi -p example.my.custom.Plugin mycustom-command
        dewi -p steven.StevenPlugin xssh ....

The exact plugin can be hidden if there is a main entry point or script:

.. code-block:: python

    #!/usr/bin/env python3
    import sys

    from dewi_core.application import Application


    def main():
        app = Application('steven')
        app.add_plugin('steven.StevenPlugin')
        app.run(sys.argv[1:])


    if __name__ == '__main__':
        main()



Usage as a regular Python library
---------------------------------

Some parts of DEWI can be used as regular Python library, without the Plugin
boilerplate. A simple example is creating a somewhat typesafe (config) tree
with the help of the now extracted dewi_dataclass_:

.. _dewi_dataclass: _DEWI: https://github.com/LA-Toth/dewi_dataclass

.. code-block:: python

    from dewi_core.config.config import Config
    from dewi_dataclass import DataClass


    class Hardware(DataClass):
        def __init__(self):
            self.hw_type: str = ''
            self.mem_size: int = None
            self.mem_free: int = None
            self.mem_mapped: int = None


    class MainNode(DataClass):
        def __init__(self):
            # Handling as str, but None is used as unset
            self.version: str = None
            self.hw = Hardware()
            # ... further fields

        def __repr__(self) -> str:
            return str(self.__dict__)


    class SampleConfig(Config):
        def __init__(self):
            super().__init__()
            self.set('root', MainNode())

        def get_main_node(self) -> MainNode:
            return self.get('root')


    # ....
    sc = SampleConfig()
    sc.get_main_node().hw.mem_size = 1024  # OK
    sc.set('root.hw.mem_size', 1024)       # OK
    sc.set('root.hw.memsize', 1024)        # NOT OK, typo

    # but...
    c = Config()
    c.set('root.hw.mem_size', 1024)  # OK
    c.set('root.hw.memsize', 1024)   # OK, but typo

As you can see, DEWI can be used as library, and it can contain slightly different
solutions of the same problem.
