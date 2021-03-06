##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test the gts ZCML namespace directives.
"""
import os
import shutil
import unittest
import threading
import tempfile
import time

import zope.component
from zope.component.testing import PlacelessSetup
from zope.configuration import xmlconfig
from zope.interface import implementer

from zope.sendmail.interfaces import \
     IMailDelivery, IMailer, ISMTPMailer
from zope.sendmail import delivery
from zope.sendmail.queue import QueueProcessorThread
import zope.sendmail.tests


class MaildirStub(object):

    def __init__(self, path, create=False):
        self.path = path
        self.create = create

    def __iter__(self):
        return iter(())

    def newMessage(self):
        return None

@implementer(IMailer)
class Mailer(object):
    pass


class DirectivesTest(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        self.mailbox = os.path.join(tempfile.mkdtemp(), "mailbox")

        super(DirectivesTest, self).setUp()
        self.testMailer = Mailer()

        gsm = zope.component.getGlobalSiteManager()
        gsm.registerUtility(Mailer(), IMailer, "test.smtp")
        gsm.registerUtility(self.testMailer, IMailer, "test.mailer")

        here = os.path.dirname(__file__)
        zcmlfile = open(os.path.join(here, "mail.zcml"), 'r')
        zcml = zcmlfile.read()
        zcmlfile.close()

        self.context = xmlconfig.string(
            zcml.replace('path/to/tmp/mailbox', self.mailbox))
        self.orig_maildir = delivery.Maildir
        delivery.Maildir = MaildirStub

    def tearDown(self):
        delivery.Maildir = self.orig_maildir

        # Tear down the mail queue processor thread.
        # Give the other thread a chance to start:
        time.sleep(0.001)
        threads = list(threading.enumerate())
        for thread in threads:
            if isinstance(thread, QueueProcessorThread):
                thread.stop()
                thread.join()

        shutil.rmtree(self.mailbox, True)
        super(DirectivesTest, self).tearDown()

    def testQueuedDelivery(self):
        delivery = zope.component.getUtility(IMailDelivery, "Mail")
        self.assertEqual('QueuedMailDelivery', delivery.__class__.__name__)
        self.assertEqual(self.mailbox, delivery.queuePath)

    def testDirectDelivery(self):
        delivery = zope.component.getUtility(IMailDelivery, "Mail2")
        self.assertEqual('DirectMailDelivery', delivery.__class__.__name__)
        self.assert_(self.testMailer is delivery.mailer)

    def testSMTPMailer(self):
        mailer = zope.component.getUtility(IMailer, "smtp")
        self.assert_(ISMTPMailer.providedBy(mailer))


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(DirectivesTest),
        ))

if __name__ == '__main__':
    unittest.main()
