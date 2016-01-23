#!/usr/bin/env python3

import datetime
import json
import logging
import time

import requests

from lenderbot import Loan


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
        try:
            # We expect a valid JSON response
            return json.loads(str(response.text))
        except:
            # We received a garbage response. Log error and return None
            self.logger.warning('Get failed. Response text: \'%s\'', response.text)
            return None

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
        try:
            # We expect a valid JSON response
            return json.loads(response.text)
        except:
            # We received a garbage response. Log error and return None
            self.logger.warning('Post failed. Response text: \'%s\'', response.text)
            return None

    def get_loans(self, showAll=False):
        loans = []
        listings = self.__execute_get('loans/listing?showAll=%s' % (showAll))
        if listings is not None and 'loans' in listings:
            raw_loans = listings['loans']
            loans = [Loan.InFundingLoan(raw_loan) for raw_loan in raw_loans]
        return loans

    def get_cash(self):
        """Retrieve available cash balance."""
        cash = self.__execute_get('accounts/%s/availablecash' % (self.iid))
        try:
            return cash['availableCash']
        except (TypeError, KeyError):
            return 0

    def get_notes_owned(self):
        """Retrieve basic information on currently owned notes."""
        mynotes = self.__execute_get('accounts/%s/notes' % (self.iid))
        try:
            return [Loan.OwnedNote(raw_loan) for raw_loan in mynotes['myNotes']]
        except (TypeError, KeyError):
            return []

    def get_detailed_notes_owned(self):
        """Retrieve detailed information on currently owned notes."""
        mynotes = self.__execute_get('accounts/%s/detailednotes' % (self.iid))
        try:
            return [Loan.DetailedOwnedNote(raw_loan) for raw_loan in mynotes['myNotes']]
        except (TypeError, KeyError):
            return []

    def submit_order(self, loans, portfolio=None, return_all=False):
        """Place a note order. Default behavior will return the execution status for successfully ordered notes."""
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
            if not isinstance(loans, list):
                loans = [loans]
            loan_dict = [{'loanId': loan['id'], 'requestedAmount': self.invest_amt} for loan in loans]
            if portfolio_id:
                for loan in loan_dict:
                    loan.update({'portfolioId': portfolio_id})
            order = json.dumps({"aid": self.iid, "orders": loan_dict})

            # Place order and return the order execution status
            order_status = self.__execute_post('accounts/%s/orders' % (self.iid), payload=order)
            try:
                # An execution status for each note is listed under the 'orderConfirmations' key.
                # Each execution status contains a list of attributes about how the order was (or
                # wasn't) fulfilled. Return the set of execution status' that were successful.
                success_status = [
                       'ORDER_FULFILLED',
                       'LOAN_AMNT_EXCEEDED',
                       'REQUESTED_AMNT_ROUNDED',
                       'AUGMENTED_BY_MERGE',
                       'NOTE_ADDED_TO_PORTFOLIO',
                       'NOT_A_VALID_PORTFOLIO',
                       'ERROR_ADDING_NOTE_TO_PORTFOLIO'
                ]
                c = order_status['orderConfirmations']
                if return_all:
                    return c
                else:
                    return [es for es in c if set(es['executionStatus']).intersection(success_status)]
            except (TypeError, KeyError):
                return []
        else:
            self.logger.info('Running in test mode. Skipping loan order')
            return []

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
        xfers = self.__execute_get('accounts/%s/funds/pending' % (self.iid))
        try:
            return xfers['transfers']
        except (TypeError, KeyError):
            return []

    def get_portfolios(self):
        """Retrieve information on all portfolios."""
        portfolios = self.__execute_get('accounts/%s/portfolios' % (self.iid))
        try:
            return portfolios['myPortfolios']
        except (TypeError, KeyError):
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
        # Portfolio doesn't exist.
        if create:
            return self.create_portfolio(name)
        return None

    def create_portfolio(self, portfolio_name, portfolio_description=None):
        """Create a portfolio."""
        if self.production_mode:
            payload = json.dumps({'aid': self.iid, 'portfolioName': portfolio_name, 'portfolioDescription': portfolio_description})
            return self.__execute_post('accounts/%d/portfolios' % (self.iid), payload=payload)
        else:
            self.logger.info('Running in test mode. Skipping portfolio creation.')
            return None
