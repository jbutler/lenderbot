#!/usr/bin/env python3

import smtplib


def send_email(recipient, subject, email_body):
    sender = 'notify@autoinvestor.io'
    message = """From: Auto-Invest <%s>
To: <%s>
Subject: %s
%s""" % (sender, recipient, subject, email_body)

    try:
        s = smtplib.SMTP('localhost')
        s.sendmail(sender, recipient, message)
    except:
        pass
    return

def email_purchase_notification(recipient, num_loans, email_body=''):
    return send_email(recipient, str(num_loans) + ' LendingClub Notes Purchased', email_body)

def email_unhandled_crash_notification(recipient, backtrace):
    return send_email(recipient, 'Uncaught exception', backtrace)

