"""
aspen.testing
+++++++++++++
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
from collections import namedtuple

from .. import resources
from ..website import Website
from filesystem_tree import FilesystemTree


CWD = os.getcwd()


def teardown():
    """Standard teardown function.

    - reset the current working directory
    - remove FSFIX = %{tempdir}/fsfix
    - reset Aspen's global state
    - clear out sys.path_importer_cache

    """
    os.chdir(CWD)
    # Reset some process-global caches. Hrm ...
    resources.__cache__ = {}
    sys.path_importer_cache = {} # see test_weird.py

teardown() # start clean


class Harness(object):
    """A harness to be used in the Aspen test suite itself. Probably not useful to you.
    """

    def __init__(self):
        self.fs = namedtuple('fs', 'www project')
        self.fs.www = FilesystemTree()
        self.fs.project = FilesystemTree()
        self._website = None

    def teardown(self):
        self.fs.www.remove()
        self.fs.project.remove()

    def hydrate_website(self, **kwargs):
        if (self._website is None) or kwargs:
            _kwargs = { 'www_root': self.fs.www.root
                      , 'project_root': self.fs.project.root
                       }
            _kwargs.update(kwargs)
            self._website = Website(**_kwargs)
        return self._website

    website = property(hydrate_website)


    # Simple API
    # ==========

    def simple(self, contents='Greetings, program!', filepath='index.html.spt', uripath=None,
            querystring='', website_configuration=None, **kw):
        """A helper to create a file and hit it through our machinery.
        """
        if filepath is not None:
            self.fs.www.mk((filepath, contents))
        if website_configuration is not None:
            self.hydrate_website(**website_configuration)

        if uripath is None:
            if filepath is None:
                uripath = '/'
            else:
                uripath = '/' + filepath
                if uripath.endswith('.spt'):
                    uripath = uripath[:-len('.spt')]
                for indexname in self.website.indices:
                    if uripath.endswith(indexname):
                        uripath = uripath[:-len(indexname)]
                        break

        return self._hit('GET', uripath, querystring, **kw)

    def _hit(self, method, path='/', querystring='', raise_immediately=True, return_after=None,
             want='response', **headers):

        state = self.website.respond( path
                                    , querystring
                                    , accept_header=None
                                    , raise_immediately=raise_immediately
                                    , return_after=return_after
                                     )

        response = state.get('response')
        if response is not None:
            if response.headers.cookie:
                self.cookie.update(response.headers.cookie)

        attr_path = want.split('.')
        base = attr_path[0]
        attr_path = attr_path[1:]

        out = state[base]
        for name in attr_path:
            out = getattr(out, name)

        return out

    def make_dispatch_result(self, *a, **kw):
        kw['return_after'] = 'dispatch_path_to_filesystem'
        kw['want'] = 'dispatch_result'
        return self.simple(*a, **kw)
