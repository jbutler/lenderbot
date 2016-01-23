#!/usr/bin/env python3

import re
import sys
import logging
from datetime import datetime, timedelta
from calendar import monthrange


class Loan(dict):
    """
    A simple class to represent a LendingClub loan.
    This is a wrapper implementing comparison methods to allow sorting.
    """

    def __init__(self, *args, **kw):
        super(Loan, self).__init__(*args, **kw)
        self.quality = 100

    def __setitem__(self, key, value):
        if key == 'quality':
            self.quality = value
        else:
            super(Loan, self).__setitem__(key, value)
        return

    def __getitem__(self, key):
        if key == 'quality':
            return self.quality
        return super(Loan, self).__getitem__(key)

    def __lt__(self, other):
        return self.quality < other.quality

    def __le__(self, other):
        return self.quality <= other.quality

    def __eq__(self, other):
        return self.quality == other.quality

    def __nq__(self, other):
        return self.quality != other.quality

    def __gt__(self, other):
        return self.quality > other.quality

    def __ge__(self, other):
        return self.quality >= other.quality

    def set_quality(self, quality):
        self.quality = quality


class InFundingLoan(Loan):
    'Implement string representation for In Funding Loans'

    def __repr__(self):
        # Print some of the more interesting loan details
        str = ''
        str += 'Loan ID: %s\n' % (self['id'])
        str += 'Amount Requested: $%d\n' % (self['loanAmount'])
        str += 'Loan purpose: %s\n' % (self['purpose'])
        str += 'Loan grade: %s\n' % (self['subGrade'])
        str += 'Interest rate: %.2f\n' % (self['intRate'])
        str += 'Loan length: %d months\n' % (self['term'])
        str += 'Monthly payment: $%d\n' % (self['installment'])
        return str


class OwnedNote(Loan):
    'Implement string representation for Owned Notes'

    def __repr__(self):
        # Print some of the more interesting note details
        str = ''
        str += 'Loan ID: %s\n' % (self['loanId'])
        str += 'Note ID: %s\n' % (self['noteId'])
        str += 'Interest rate: %.2f\n' % (self['interestRate'])
        str += 'Loan length: %d months\n' % (self['loanLength'])
        return str


class DetailedOwnedNote(Loan):
    'Implement string representation for Detailed Owned Notes'

    def __repr__(self):
        # Print some of the more interesting note details
        str = ''
        str += 'Loan ID: %s\n' % (self['loanId'])
        str += 'Note ID: %s\n' % (self['noteId'])
        str += 'Loan amount: %d\n' % (self['loanAmount'])
        str += 'Loan purpose: %s\n' % (self['purpose'])
        str += 'Loan grade: %s\n' % (self['grade'])
        str += 'Interest rate: %.2f\n' % (self['interestRate'])
        str += 'Loan length: %d months\n' % (self['loanLength'])
        str += 'Loan status: %s\n' % (self['loanStatus'])
        str += 'Payments received: $%.2f\n' % (self['paymentsReceived'])
        return str

    def is_fully_paid(self):
        return self['loanStatus'] == 'Fully Paid'

    def is_charged_off(self):
        return self['loanStatus'] == 'Charged Off'

    def is_late(self):
        return 'Late' in self['loanStatus']

    def is_current(self):
        return self['loanStatus'] == 'Current' or self['loanStatus'] == 'Issued'

    def is_open(self):
        return not self.is_fully_paid() and not self.is_charged_off()

    def is_issued(self):
        return not self['loanStatus'] == 'In Review'


class PastLoan(Loan):
    'A simple class to represent a historical LendingClub loan.'

    def __init__(self, badKey, badVal, *args, **kw):
        super(PastLoan, self).__init__(*args, **kw)

        self._valid = self._sanitize(badKey, badVal)

    def isValid(self):
        return self._valid

    def getAge(self):
        if 'loan_age' not in self:
            self['loan_age'] = self._calcAge()
        return self['loan_age']

    def _calcAge(self):
        # Expects dates to be of the form 'Dec-2015'
        start = datetime.strptime(str(self['issue_d']), '%b-%Y')
        end = datetime.strptime(str(self['last_pymnt_d']), '%b-%Y')

        # Count the months between issue date and last payment
        months = 0
        while (start < end):
            # Get number of days of start's current month
            mdays = monthrange(start.year, start.month)[1]
            start += timedelta(days=mdays)

            # If end >= (start + start.month[days]), count this month
            if end >= start:
                months += 1

        return months

    def _sanitize(self, badKey, badVal):
        valid = True

        # Used for debugging
        if 'csv_line' not in self:
            self['csv_line'] = "-1"

        # Catch bad formatting
        if badKey in self:
            logging.debug(badKey, ''.join(self[badKey]))
            logging.debug("Bad Key")
            valid = False

        if 'last_pymnt_d' in self and re.match("^\s*$", self['last_pymnt_d']):
            if 'issue_d' in self:
                # If no payment received, last payment date = issue date
                self['last_pymnt_d'] = self['issue_d']

        for k, v in self.items():
            if badVal == v:
                logging.debug(badVal)
                valid = False
                break

            # Replace empties with 0s
            if re.match('^\s*$', str(v)):
                self[k] = 0

        if not valid:
            logging.debug(self.items())
            # Can't safely access specific keys, other than id, when incorrectly formatted
            logging.warning("Fix Loan {}".format(self['id']))
            logging.warning("Line {}".format(self['csv_line']))

        return valid
