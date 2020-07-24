from __future__ import absolute_import
from multiprocessing import Manager
share = Manager().dict()
from .dht import table