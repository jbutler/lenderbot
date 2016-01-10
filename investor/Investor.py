#!/usr/bin/env python3

import datetime
import json
import logging
import time

import requests

from investor import Loan


class Investor:
    """A simple class to interact with your LendingClub account."""

    def __init__(self, iid, auth_key, invest_amt=25, production_mode=False):
        self.iid = iid
        self.headers = {'Authorization': auth_key, 'Accept': 'application/json', 'Content-type': 'application/json'}
        self.endpoint_root = 'https://api.lendingclub.com/api/investor/v1/'
        self.invest_amt = invest_amt
        self.production_mode = production_mode
        self.logger = logging.getLogger(__name__)
        self.time_delay = datetime.timedelta(seconds=1)  # We must wait one second between requests
        self.last_request_ts = datetime.datetime.min  # No requests have been made yet
        self.max_log_len = 1024
        self.filters = []
        self.my_note_ids = [x['loanId'] for x in self.get_notes_owned()]

    def __set_ts(self):
        self.last_request_ts = datetime.datetime.now()
        return

    def __get_ts(self):
        return self.last_request_ts

    def __execute_delay(self):
        cur_time = datetime.datetime.now()
        delta = cur_time - self.__get_ts()
        if delta < self.time_delay:
            # Round up sleep time to the nearest second
            sleep_time = (delta + datetime.timedelta(milliseconds=999)).seconds
            time.sleep(sleep_time)
        return

    def __execute_get(self, url, log=True):
        self.__execute_delay()
        endpoint = self.endpoint_root + url
        response = requests.get(endpoint, headers=self.headers)
        self.__set_ts()
        if log and len(response.text) < self.max_log_len:
            self.logger.debug('-------- GET BEGIN --------')
            self.logger.debug('Endpoint: %s', endpoint)
            self.logger.debug('Headers:  %s', self.headers)
            self.logger.debug('Response: %s | %s', response, response.text)
            self.logger.debug('--------- GET END ---------')
        return response.text

    def __execute_post(self, url, payload=None, log=True):
        self.__execute_delay()
        endpoint = self.endpoint_root + url
        response = requests.post(endpoint, data=payload, headers=self.headers)
        self.__set_ts()
        if log and len(response.text) < self.max_log_len:
            self.logger.debug('-------- POST BEGIN --------')
            self.logger.debug('Endpoint: %s', endpoint)
            self.logger.debug('Data:     %s', payload)
            self.logger.debug('Headers:  %s', self.headers)
            self.logger.debug('Response: %s | %s', response, response.text)
            self.logger.debug('--------- POST END ---------')
        return response.text

    def __apply_filters(self, loans):
        # First, filter out loans we already own
        loans = [loan for loan in loans if loan['id'] not in self.my_note_ids]

        # Second, apply user defined filters
        for f in self.filters:
            loans = [loan for loan in loans if f.apply(loan)]
        return loans

    def __get_loans(self, showAll=False):
        loans = []
        listings_json = self.__execute_get('loans/listing?showAll=%s' % (showAll))
        try:
            raw_loans = json.loads(listings_json)['loans']
            loans = [Loan.InFundingLoan(raw_loan) for raw_loan in raw_loans]
        except:
            # Key error, most likely
            self.logger.warning('Loan retrieval failed. Response text:\n  -- %s', listings_json)
        return loans

    def add_filters(self, filters):
        """Add filters."""
        self.filters.extend(filters)

    def test_filters(self):
        """Test filters by applying each one to every currently available loan."""
        loans = self.__get_loans(showAll=True)
        for f in self.filters:
            self.logger.info('Testing filter: %s', f)
            for l in loans:
                f.apply(l)

    def get_cash(self):
        """Retrieve available cash balance."""
        cash = self.__execute_get('accounts/%s/availablecash' % (self.iid))
        if not cash:
            return 0
        return json.loads(cash)['availableCash']

    def get_new_loans(self, showAll=False):
        """Retrieve newly listed loans that pass filters."""
        for _ in range(1, 140):
            loans = self.__get_loans(showAll)
            loans = self.__apply_filters(loans)
            if len(loans):
                return loans
        return []

    def get_notes_owned(self):
        """Retrieve basic information on currently owned notes."""
        mynotes = self.__execute_get('accounts/%s/notes' % (self.iid))
        if mynotes:
            return [Loan.OwnedNote(raw_loan) for raw_loan in json.loads(mynotes)['myNotes']]
        else:
            self.logger.warning('Error retrieving owned notes: %s', mynotes)
        return None

    def get_detailed_notes_owned(self):
        """Retrieve detailed information on currently owned notes."""
        mynotes = self.__execute_get('accounts/%s/detailednotes' % (self.iid))
        if mynotes:
            return [Loan.DetailedOwnedNote(raw_loan) for raw_loan in json.loads(mynotes)['myNotes']]
        else:
            self.logger.warning('Error retrieving owned notes: %s', mynotes)
        return None

    def submit_order(self, loans, portfolio=None):
        """Place a note order."""
        if self.production_mode:
            # Portfolio parameter can either be a dictionary or portfolio ID
            portfolio_id = None
            if isinstance(portfolio, dict):
                portfolio_id = portfolio['portfolioId']
            elif isinstance(portfolio, str):
                portfolio_id = portfolio
            elif portfolio is not None:
                self.logger.error('Invalid portfolio type passed to submit_order()')

            # Construction order payload
            loan_dict = [{'loanId': loan['id'], 'requestedAmount': self.invest_amt} for loan in loans]
            if portfolio_id:
                for loan in loan_dict:
                    loan.update({'portfolioId': portfolio_id})
            order = json.dumps({"aid": self.iid, "orders": loan_dict})
            return self.__execute_post('accounts/%s/orders' % (self.iid), payload=order)
        else:
            self.logger.info('Running in test mode. Skipping loan order')
            return None

    def add_funds(self, amount):
        """Initiate bank transfer to fund account."""
        if self.production_mode:
            payload = json.dumps({'amount': amount, 'transferFrequency': 'LOAD_NOW'})
            return self.__execute_post('accounts/%s/funds/add' % (self.iid), payload=payload)
        else:
            self.logger.info('Running in test mode. Skipping money transfer.')
            return None

    def get_pending_transfers(self):
        """Retrieve information on current pending bank transfers."""
        xfers = json.loads(self.__execute_get('accounts/%s/funds/pending' % (self.iid)))
        if 'transfers' in xfers:
            return xfers['transfers']
        else:
            return []

    def get_portfolios(self):
        """Retrieve information on all portfolios."""
        portfolios = json.loads(self.__execute_get('accounts/%s/portfolios' % (self.iid)))
        try:
            return portfolios['myPortfolios']
        except KeyError:
            return []

    def get_portfolio(self, name, create=False):
        """
        Retrieve information on a specific portfolio.
        Optionally create the portfolio if it does not exist.
        """
        # Return requested portfolio, if it exists
        portfolios = self.get_portfolios()
        for p in portfolios:
            if p['portfolioName'] == name:
                return p
        # Portfolio doesn't exist
        if create:
            return self.create_portfolio(name)

    def create_portfolio(self, portfolio_name, portfolio_description=None):
        """Create a portfolio."""
        if self.production_mode:
            payload = json.dumps({'aid': self.iid, 'portfolioName': portfolio_name, 'portfolioDescription': portfolio_description})
            return self.__execute_post('accounts/%d/portfolios' % (self.iid), payload=payload)
        else:
            self.logger.info('Running in test mode. Skipping portfolio creation.')
            return None
