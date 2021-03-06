#!/usr/bin/python
# -*- coding: utf-8 -*-
# rdiffweb, A web interface to rdiff-backup repositories
# Copyright (C) 2019 rdiffweb contributors
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

"""
Created on Oct 14, 2015

Module to test `user` module.

@author: Patrik Dufresne <info@patrikdufresne.com>
"""

from __future__ import unicode_literals

from _io import StringIO
from builtins import str
from io import open
import logging
from mock import MagicMock
import os
import unittest

from mockldap import MockLdap
import pkg_resources

from rdiffweb.core import RdiffError, authorizedkeys
from rdiffweb.core.store import IUserChangeListener
from rdiffweb.test import AppTestCase


def _ldap_user(name, password='password'):
    """Create ldap entry to be mock."""
    assert isinstance(name, str)
    assert isinstance(password, str)
    return ('uid=%s,ou=People,dc=nodomain' % (name), {
        'uid': [name],
        'cn': [name],
        'userPassword': [password],
        'objectClass': ['person', 'organizationalPerson', 'inetOrgPerson', 'posixAccount']})


class StoreSQLiteTest(AppTestCase):

    def setUp(self):
        AppTestCase.setUp(self)
        self.mlistener = IUserChangeListener(self.app)
        self.mlistener.user_added = MagicMock()
        self.mlistener.user_attr_changed = MagicMock()
        self.mlistener.user_deleted = MagicMock()
        self.mlistener.user_logined = MagicMock()
        self.mlistener.user_password_changed = MagicMock()

    def test_add_user(self):
        """Add user to database."""
        userobj = self.app.store.add_user('joe')
        self.assertIsNotNone(userobj)
        self.assertIsNotNone(self.app.store.get_user('joe'))
        # Check if listener called
        self.mlistener.user_added.assert_called_once_with(userobj, None)

    def test_add_user_with_duplicate(self):
        """Add user to database."""
        userobj = self.app.store.add_user('denise')
        with self.assertRaises(RdiffError):
            self.app.store.add_user('denise')
        # Check if listener called
        self.mlistener.user_added.assert_called_once_with(userobj, None)

    def test_add_user_with_password(self):
        """Add user to database with password."""
        userobj = self.app.store.add_user('jo', 'password')
        self.assertIsNotNone(self.app.store.get_user('jo'))
        self.assertTrue(self.app.store.login('jo', 'password'))
        # Check if listener called
        self.mlistener.user_added.assert_called_once_with(userobj, None)

    def test_delete_admin_user(self):
        # Trying to delete admin user should raise an error.
        userobj = self.app.store.add_user('admin')
        with self.assertRaises(ValueError):
            userobj.delete()

    def test_delete_user(self):
        # Create user
        userobj = self.app.store.add_user('vicky', 'password')
        self.assertIsNotNone(self.app.store.get_user('vicky'))
        # Delete user
        userobj.delete()
        self.assertIsNone(self.app.store.get_user('vicky'))
        # Check if listener called
        self.mlistener.user_deleted.assert_called_once_with('vicky')

    def test_get_user(self):
        """
        Test user record.
        """
        # Create new user
        user = self.app.store.add_user('bernie', 'my-password')
        user.user_root = '/backups/bernie/'
        user.is_admin = True
        user.email = 'bernie@gmail.com'
        user.repos = ['computer', 'laptop']
        user.repo_objs[0].maxage = -1
        user.get_repo('bernie/laptop').maxage = 3

        # Get user record.
        obj = self.app.store.get_user('bernie')
        self.assertIsNotNone(obj)
        self.assertEqual('bernie', obj.username)
        self.assertEqual('bernie@gmail.com', obj.email)
        self.assertEqual(['computer', 'laptop'], obj.repos)
        self.assertEqual('/backups/bernie/', obj.user_root)
        self.assertEqual(True, obj.is_admin)

        # Get repo object
        self.assertEqual('computer', obj.repo_objs[0].name)
        self.assertEqual(-1, obj.repo_objs[0].maxage)
        self.assertEqual('laptop', obj.get_repo('bernie/laptop').name)
        self.assertEqual(3, obj.get_repo('bernie/laptop').maxage)
        
    def test_get_set(self):
        user = self.app.store.add_user('larry', 'password')

        self.assertEqual('', user.email)
        self.assertEqual([], user.repos)
        self.assertEqual('', user.user_root)
        self.assertEqual(False, user.is_admin)

        user.user_root = '/backups/'
        self.mlistener.user_attr_changed.assert_called_with(user, {'user_root': '/backups/'})
        user.is_admin = True
        self.mlistener.user_attr_changed.assert_called_with(user, {'is_admin': True})
        user.email = 'larry@gmail.com'
        self.mlistener.user_attr_changed.assert_called_with(user, {'email': 'larry@gmail.com'})
        user.repos = ['computer', 'laptop']
        self.mlistener.user_attr_changed.assert_called_with(user, {'repos': ['computer', 'laptop']})

        self.assertEqual('larry@gmail.com', user.email)
        self.assertEqual(['computer', 'laptop'], user.repos)
        self.assertEqual('/backups/', user.user_root)
        self.assertEqual(True, user.is_admin)

    def test_users(self):
        self.assertEqual([], list(self.app.store.users()))
        self.app.store.add_user('annik')
        users = list(self.app.store.users())
        self.assertEqual(1, len(users))
        self.assertEqual('annik', users[0].username)
        self.assertEqual(1, self.app.store.count_users())

    def test_users_with_search(self):
        self.assertEqual([], list(self.app.store.users()))
        self.app.store.add_user('annik')
        self.app.store.add_user('tom')
        self.app.store.add_user('jeff')
        self.app.store.add_user('josh')
        users = list(self.app.store.users(search='j'))
        self.assertEqual(2, len(users))
        self.assertEqual('jeff', users[0].username)
        self.assertEqual('josh', users[1].username)
        self.assertEqual(4, self.app.store.count_users())
        
    def test_users_with_criteria_admins(self):
        self.assertEqual([], list(self.app.store.users()))
        self.app.store.add_user('annik').is_admin = True
        self.app.store.add_user('tom').is_admin = True
        self.app.store.add_user('jeff')
        self.app.store.add_user('josh')
        users = list(self.app.store.users(criteria='admins'))
        self.assertEqual(2, len(users))
        self.assertEqual('annik', users[0].username)
        self.assertEqual('tom', users[1].username)
        
    def test_users_with_criteria_ldap(self):
        self.assertEqual([], list(self.app.store.users()))
        self.app.store.add_user('annik', 'coucou')
        self.app.store.add_user('tom')
        users = list(self.app.store.users(criteria='ldap'))
        self.assertEqual(1, len(users))
        self.assertEqual('tom', users[0].username)
        
    def test_users_with_criteria_invalid(self):
        self.assertEqual([], list(self.app.store.users()))
        self.app.store.add_user('annik', 'coucou')
        self.app.store.add_user('tom')
        users = list(self.app.store.users(criteria='invalid'))
        self.assertEqual(0, len(users))
        
    def test_login(self):
        """Check if login work"""
        userobj = self.app.store.add_user('tom', 'password')
        self.assertIsNotNone(self.app.store.login('tom', 'password'))
        self.assertFalse(self.app.store.login('tom', 'invalid'))
        # Check if listener called
        self.mlistener.user_logined.assert_called_once_with(userobj, None)

    def login_with_invalid_password(self):
        self.app.store.add_user('jeff', 'password')
        self.assertFalse(self.app.store.login('jeff', 'invalid'))
        # password is case sensitive
        self.assertFalse(self.app.store.login('jeff', 'Password'))
        # Match entire password
        self.assertFalse(self.app.store.login('jeff', 'pass'))
        self.assertFalse(self.app.store.login('jeff', ''))
        # Check if listener called
        self.mlistener.user_logined.assert_not_called()

    def test_login_with_invalid_user(self):
        """Check if login work"""
        self.assertIsNone(self.app.store.login('josh', 'password'))
        # Check if listener called
        self.mlistener.user_logined.assert_not_called()

    def test_repos(self):
        self.assertEqual([], list(self.app.store.repos()))
        user_obj = self.app.store.add_user('annik')
        user_obj.repos = ['laptop', 'desktop']
        user_obj = self.app.store.add_user('kim')
        user_obj.repos = ['repo1']
        
        data = list(self.app.store.repos())
        self.assertEqual(3, len(data))
        self.assertEqual('annik', data[0].owner)
        self.assertEqual('laptop', data[0].name)

    def test_search(self):
        """
        Check if search is working.
        """
        self.app.store.add_user('Charlie', 'password')
        self.app.store.add_user('Bernard', 'password')
        self.app.store.add_user('Kim', 'password')
        users = list(self.app.store.users())
        self.assertEqual(3, len(users))

    def test_set_password_update(self):
        userobj = self.app.store.add_user('annik', 'password')
        userobj.set_password('new_password')
        # Check new credentials
        self.assertIsNotNone(self.app.store.login('annik', 'new_password'))
        # Check if listener called
        self.mlistener.user_password_changed.assert_called_once_with('annik', 'new_password')

    def test_set_password_with_old_password(self):
        userobj = self.app.store.add_user('john', 'password')
        userobj.set_password('new_password', old_password='password')
        # Check new credentials
        self.assertIsNotNone(self.app.store.login('john', 'new_password'))
        # Check if listener called
        self.mlistener.user_password_changed.assert_called_once_with('john', 'new_password')

    def test_set_password_with_invalid_old_password(self):
        userobj = self.app.store.add_user('foo', 'password')
        with self.assertRaises(ValueError):
            userobj.set_password('new_password', old_password='invalid')
        # Check if listener called
        self.mlistener.user_password_changed.assert_not_called()


class StoreWithLdapTest(AppTestCase):

    basedn = ('dc=nodomain', {
        'dc': ['nodomain'],
        'o': ['nodomain']})
    people = ('ou=People,dc=nodomain', {
        'ou': ['People'],
        'objectClass': ['organizationalUnit']})

    # This is the content of our mock LDAP directory. It takes the form
    # {dn: {attr: [value, ...], ...}, ...}.
    directory = dict([
        basedn,
        people,
        _ldap_user('annik'),
        _ldap_user('bob'),
        _ldap_user('foo'),
        _ldap_user('jeff'),
        _ldap_user('john'),
        _ldap_user('karl'),
        _ldap_user('kim'),
        _ldap_user('larry'),
        _ldap_user('mike'),
        _ldap_user('tony'),
        _ldap_user('vicky'),
    ])

    default_config = {
        'LdapUri': '__default__',
        'LdapBaseDn': 'dc=nodomain',
        'LdapAllowPasswordChange': 'true'
    }

    @classmethod
    def setUpClass(cls):
        # We only need to create the MockLdap instance once. The content we
        # pass in will be used for all LDAP connections.
        cls.mockldap = MockLdap(cls.directory)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        # Mock LDAP
        self.mockldap.start()
        self.ldapobj = self.mockldap['ldap://localhost/']
        # Original setup
        AppTestCase.setUp(self)
        # Get reference to LdapStore
        self.ldapstore = self.app.store._password_stores[0]
        # Create fake listener
        self.mlistener = IUserChangeListener(self.app)
        self.mlistener.user_added = MagicMock()
        self.mlistener.user_attr_changed = MagicMock()
        self.mlistener.user_deleted = MagicMock()
        self.mlistener.user_logined = MagicMock()
        self.mlistener.user_password_changed = MagicMock()

    def tearDown(self):
        # Stop patching ldap.initialize and reset state.
        self.mockldap.stop()
        del self.ldapobj
        AppTestCase.tearDown(self)

    def test_add_user_to_sqlite(self):
        """Add user to local database."""
        self.app.store.add_user('joe', 'password')
        userobj = self.app.store.login('joe', 'password')
        self.assertIsNotNone(userobj)
        self.assertEqual('joe', userobj.username)
        # Check if listener called
        self.mlistener.user_added.assert_called_once_with(userobj, None)

    def test_add_user_to_ldap(self):
        """Add user to LDAP."""
        self.app.store.add_user('karl', 'password')
        userobj = self.app.store.login('karl', 'password')
        self.assertIsNotNone(userobj)
        self.assertEqual('karl', userobj.username)
        # Check if listener called
        self.mlistener.user_added.assert_called_once_with(userobj, None)

    def test_delete_user(self):
        """Create then delete a user."""
        # Create user
        userobj = self.app.store.add_user('vicky')
        self.assertIsNotNone(self.app.store.get_user('vicky'))
        self.assertIsNotNone(self.app.store.login('vicky', 'password'))
        # Delete user.
        self.assertTrue(userobj.delete())
        self.assertIsNone(self.app.store.get_user('vicky'))

    def test_get_user_with_invalid_user(self):
        self.assertIsNone(self.app.store.get_user('invalid'))

    def test_get_set(self):
        username = 'larry'
        user = self.app.store.add_user(username, 'password')

        self.assertEqual('', user.email)
        self.assertEqual([], user.repos)
        self.assertEqual('', user.user_root)
        self.assertEqual(False, user.is_admin)

        user.user_root = '/backups/'
        user.is_admin = True
        user.email = 'larry@gmail.com'
        user.repos = ['computer', 'laptop']

        user = self.app.store.get_user(username)
        self.assertEqual('larry@gmail.com', user.email)
        self.assertEqual(['computer', 'laptop'], user.repos)
        self.assertEqual('/backups/', user.user_root)

    def test_list(self):
        self.assertEqual([], list(self.app.store.users()))
        self.app.store.add_user('annik')
        users = list(self.app.store.users())
        self.assertEqual('annik', users[0].username)

    def test_login(self):
        """Check if login work"""
        self.app.store.add_user('tom', 'password')
        self.assertIsNotNone(self.app.store.login('tom', 'password'))
        self.assertIsNone(self.app.store.login('tom', 'invalid'))

    def test_login_with_invalid_password(self):
        self.app.store.add_user('jeff', 'password')
        self.assertIsNone(self.app.store.login('jeff', 'invalid'))
        # password is case sensitive
        self.assertIsNone(self.app.store.login('jeff', 'Password'))
        # Match entire password
        self.assertIsNone(self.app.store.login('jeff', 'pass'))
        self.assertIsNone(self.app.store.login('jeff', ''))

    def test_login_with_invalid_user(self):
        """Check if login work"""
        self.assertIsNone(self.app.store.login('josh', 'password'))

    def test_login_with_invalid_user_in_ldap(self):
        """Check if login work"""
        self.assertIsNone(self.app.store.login('kim', 'password'))

    def test_login_with_create_user(self):
        """Check if login create the user in database if user exists in LDAP"""
        self.assertIsNone(self.app.store.get_user('tony'))
        self.app.cfg['addmissinguser'] = 'true'
        try:
            userobj = self.app.store.login('tony', 'password')
            self.assertIsNotNone(self.app.store.get_user('tony'))
            self.assertFalse(userobj.is_admin)
            # Check listener
            self.mlistener.user_added.assert_called_once_with(userobj, {u'objectClass': [u'person', u'organizationalPerson', u'inetOrgPerson', u'posixAccount'], u'userPassword': [u'password'], u'uid': [u'tony'], u'cn': [u'tony']})
            self.mlistener.user_logined.assert_called_once_with(userobj, {u'objectClass': [u'person', u'organizationalPerson', u'inetOrgPerson', u'posixAccount'], u'userPassword': [u'password'], u'uid': [u'tony'], u'cn': [u'tony']})
        finally:
            self.app.cfg['addmissinguser'] = 'false'

    def test_get_user_invalid(self):
        self.assertIsNone(self.app.store.get_user('invalid'))

    def test_set_password_update(self):
        userobj = self.app.store.add_user('annik')
        self.assertFalse(userobj.set_password('new_password'))
        # Check new credentials
        self.assertIsNotNone(self.app.store.login('annik', 'new_password'))

    def test_set_password_with_old_password(self):
        userobj = self.app.store.add_user('john')
        userobj.set_password('new_password', old_password='password')
        # Check new credentials
        self.assertIsNotNone(self.app.store.login('john', 'new_password'))

    def test_set_password_with_invalid_old_password(self):
        userobj = self.app.store.add_user('foo')
        with self.assertRaises(ValueError):
            userobj.set_password('new_password', old_password='invalid')

    def test_set_password_empty(self):
        """Expect error when trying to update password of invalid user."""
        userobj = self.app.store.add_user('john')
        with self.assertRaises(ValueError):
            self.assertFalse(userobj.set_password(''))


class StoreWithAdmin(AppTestCase):
    
    reset_testcases = True

    REPO = 'testcases/'

    USERNAME = 'admin'

    PASSWORD = 'admin123'
    
    def test_disk_quota(self):
        """
        Just make a call to the function.
        """
        userobj = self.app.store.get_user(self.USERNAME)
        userobj.disk_quota

    def test_disk_usage(self):
        """
        Just make a call to the function.
        """
        userobj = self.app.store.get_user(self.USERNAME)
        disk_usage = userobj.disk_usage
        self.assertIn('avail', disk_usage)
        self.assertIn('used', disk_usage)
        self.assertIn('size', disk_usage)


class StoreTestSSHKeys(AppTestCase):
    """
    Testcases for ssh key management.
    """
    reset_testcases = True

    REPO = 'testcases/'

    USERNAME = 'admin'

    PASSWORD = 'admin123'
    
    def _read_ssh_key(self):
        """Readthe pub key from test packages"""
        filename = pkg_resources.resource_filename(__name__, 'test_publickey_ssh_rsa.pub')  # @UndefinedVariable
        with open(filename, 'r', encoding='utf8') as f: 
            return f.readline()
        
    def _read_authorized_keys(self):
        """Read the content of test_authorized_keys"""
        filename = pkg_resources.resource_filename(__name__, 'test_authorized_keys')  # @UndefinedVariable
        with open(filename, 'r', encoding='utf8') as f: 
            return f.read()
   
    def test_add_authorizedkey_without_file(self):
        """
        Add an ssh key for a user without an authorizedkey file.
        """
        # Read the pub key
        key = self._read_ssh_key()
        # Add the key to the user
        userobj = self.app.store.get_user(self.USERNAME)
        userobj.add_authorizedkey(key)
        
        # validate
        keys = list(userobj.authorizedkeys)
        self.assertEqual(1, len(keys), "expecting one key")
        self.assertEqual("3c:99:ed:a7:82:a8:71:09:2c:15:3d:78:4a:8c:11:99", keys[0].fingerprint)

    def test_add_authorizedkey_with_file(self):
        """
        Add an ssh key for a user with an authorizedkey file.
        """
        userobj = self.app.store.get_user(self.USERNAME)

        # Create empty authorized_keys file
        os.mkdir(os.path.join(userobj.user_root, '.ssh'))
        filename = os.path.join(userobj.user_root, '.ssh', 'authorized_keys')
        open(filename, 'a').close()
        
        # Read the pub key
        key = self._read_ssh_key()
        userobj.add_authorizedkey(key)
        
        # Validate
        with open(filename, 'r') as fh:
            self.assertEqual(key, fh.read())
            
    def test_remove_authorizedkey_without_file(self):
        """
        Remove an ssh key for a user without authorizedkey file.
        """
        # Update user with ssh keys.
        data = self._read_authorized_keys()
        userobj = self.app.store.get_user(self.USERNAME)
        for k in authorizedkeys.read(StringIO(data)):
            try:
                userobj.add_authorizedkey(k.getvalue())
            except:
                pass
        
        # Get the keys
        keys = list(userobj.authorizedkeys)
        self.assertEqual(2, len(keys))
        
        # Remove a key
        userobj.remove_authorizedkey("9a:f1:69:3c:bc:5a:cd:02:5e:33:bc:cd:c0:01:eb:4c")

        # Validate
        keys = list(userobj.authorizedkeys)
        self.assertEqual(1, len(keys))
        
    def test_remove_authorizedkey_with_file(self):
        """
        Remove an ssh key for a user with authorizedkey file.
        """
        # Create authorized_keys file
        data = self._read_authorized_keys()
        userobj = self.app.store.get_user(self.USERNAME)
        os.mkdir(os.path.join(userobj.user_root, '.ssh'))
        filename = os.path.join(userobj.user_root, '.ssh', 'authorized_keys')
        with open(filename, 'w') as f :
            f.write(data)
        
        # Get the keys
        keys = list(userobj.authorizedkeys)
        self.assertEqual(5, len(keys))
        
        # Remove a key
        userobj.remove_authorizedkey("9a:f1:69:3c:bc:5a:cd:02:5e:33:bc:cd:c0:01:eb:4c")

        # Validate
        keys = list(userobj.authorizedkeys)
        self.assertEqual(4, len(keys))


class UserObjectTest(AppTestCase):
    """Testcases for UserObject"""
    
    reset_testcases = True

    REPO = 'testcases/'

    USERNAME = 'admin'

    PASSWORD = 'admin123'
    
    def test_set_get_repos(self):
        userobj = self.app.store.get_user(self.USERNAME)
        self.assertEquals(['testcases'], userobj.repos)
        
        # Test empty list
        userobj.repos = []
        self.assertEquals([], userobj.repos)
        
        # Test with leading & ending "/"
        userobj.repos = ["/testcases/"]
        self.assertEquals(["testcases"], userobj.repos)
        self.assertEqual(1, len(userobj.repo_objs))
        self.assertEqual("testcases", userobj.repo_objs[0].name)
        
        # Make sure we get a repo
        repo_obj = userobj.get_repo('admin/testcases')
        self.assertEquals("testcases", repo_obj.name)
        repo_obj.maxage = 10
        self.assertEquals(10, repo_obj.maxage)
        
        # Make sure we get a repo_path
        repo_obj, path_obj = userobj.get_repo_path('admin/testcases')
        repo_obj.maxage = 7
        self.assertEquals(7, repo_obj.maxage)


class RepoObjectTest(AppTestCase):
    """Testcases for RepoObject."""
    
    reset_testcases = True

    USERNAME = 'admin'

    PASSWORD = 'admin123'

    def test_set_get_encoding(self):
        userobj = self.app.store.get_user(self.USERNAME)
        repo_obj = userobj.get_repo(self.REPO)
        repo_obj.encoding = "cp1252"
        self.assertEqual("cp1252", repo_obj.encoding)
        # Check with invalid value.
        with self.assertRaises(ValueError):
            repo_obj.encoding = "invalid"
            
    def test_set_get_maxage(self):
        userobj = self.app.store.get_user(self.USERNAME)
        repo_obj = userobj.get_repo(self.REPO)
        repo_obj.maxage = 10
        self.assertEqual(10, repo_obj.maxage)
        # Check with invalid value.
        with self.assertRaises(ValueError):
            repo_obj.maxage = "invalid"

    def test_set_get_keepdays(self):
        userobj = self.app.store.get_user(self.USERNAME)
        repo_obj = userobj.get_repo(self.REPO)
        repo_obj.keepdays = 10
        self.assertEqual(10, repo_obj.keepdays)
        # Check with invalid value.
        with self.assertRaises(ValueError):
            repo_obj.keepdays = "invalid"


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
