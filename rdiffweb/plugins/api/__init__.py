#!/usr/bin/python
# -*- coding: utf-8 -*-
# rdiffweb, A web interface to rdiff-backup repositories
# Copyright (C) 2014 rdiffweb contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import cherrypy
from future.utils import native_str
import logging
import os
import pkg_resources

from rdiffweb import librdiff
from rdiffweb.dispatch import static, empty
from rdiffweb.rdw_plugin import IRdiffwebPlugin


# Define the logger
logger = logging.getLogger(__name__)


@cherrypy.config(**{'tools.authform.on': False, 'tools.i18n.on': False, 'tools.authbasic.on': True, 'tools.sessions.on': False, 'error_page.default': False})
class ApiPlugin(IRdiffwebPlugin):
    """
    This plugin provide a restful API to access some of the rdiffweb resources.
    """

    def activate(self):
        # Register our self in the application tree.
        self.app.root.api = empty()
        self.app.root.api.v1 = self

        # Activate plugin.
        IRdiffwebPlugin.activate(self)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def repositories(self):
        """
        Return the list of repositories.
        """
        return self.app.currentuser.repos
