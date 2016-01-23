#!/usr/bin/env python3

from datetime import datetime
import json
import logging.config
import os

from lenderbot import Investor
from lenderbot import LoanFilter

DEFAULT_CFG_DIR = os.path.join(os.path.expanduser('~'), '.lenderbot')
EXECUTION_CFG = 'config.json'
LOGGER_CFG = 'logging.json'
FILTERS_CFG = 'filters.json'
PRODUCTION_MODE_WARNING = '''Entering production mode. lenderbot may invest in loans or transfer money into your lending account according to your configuration.'''

def lenderbot_get_config_dir(config_dir):
    if not config_dir:
        return DEFAULT_CFG_DIR
    return config_dir

def lenderbot_get_config(config_dir, cfg_file):
    cfg = os.path.join(lenderbot_get_config_dir(config_dir), cfg_file)
    with open(cfg) as cf_handle:
        return json.load(cf_handle)

def lenderbot_init_config(config_dir):
    # There's no processing, yet
    return lenderbot_get_config(config_dir, EXECUTION_CFG)

def lenderbot_init_logger(config_dir):
    cfg_dir = lenderbot_get_config_dir(config_dir)
    cfg = lenderbot_get_config(config_dir, LOGGER_CFG)
    for handler in cfg['handlers']:
        handler = cfg['handlers'][handler]
        if 'filename' in handler:
            handler['filename'] = os.path.join(cfg_dir, handler['filename'])
    logging.config.dictConfig(cfg)
    return logging.getLogger()

def lenderbot_init_filters(config_dir):
    cfg = lenderbot_get_config(config_dir, FILTERS_CFG)
    filters = []
    if 'filters' in cfg:
        for rule in cfg['filters']:
            filters.append(LoanFilter.BasicFilter(rule))
    return filters

def lenderbot_init_driver(cfg, production_mode):
    # Eventually we'll support multiple driver types, but for now
    # we only support LendingClub
    return Investor.Investor(cfg['account']['iid'],
                             cfg['account']['auth'],
                             invest_amt=cfg['account']['orderamnt'],
                             production_mode=production_mode)

def lenderbot_get_portfolio(cfg):
    if 'portfolio' in cfg['account']:
        return datetime.now().__format__(cfg['account']['portfolio'])
    return None

class LenderBot:
    """Automated investing for your P2P lending accounts."""

    def __init__(self, config_dir=None, production_mode=True):
        self.config = lenderbot_init_config(config_dir)
        self.logger = lenderbot_init_logger(config_dir)
        self.filters = lenderbot_init_filters(config_dir)
        self.driver = lenderbot_init_driver(self.config, production_mode)
        self.my_note_ids = [x['loanId'] for x in self.driver.get_notes_owned()]
        if production_mode:
            self.logger.warning(PRODUCTION_MODE_WARNING)
        self.logger.info('Adding %d filter(s)', len(self.filters))
        self.logger.info('LenderBot initialization complete')

    def __apply_filters(self, loans):
        # First, filter out loans we already own
        loans = [loan for loan in loans if loan['id'] not in self.my_note_ids]

        # Second, apply user defined filters
        for f in self.filters:
            loans = [loan for loan in loans if f.apply(loan)]
        return loans

    def run(self):
        self.find_late_notes()
        self.invest()
        self.fund_account()

    def note_summary(self, late_only=False, include_closed=False):
        # TODO: Revisit this
        # Get full list of owned notes
        notes = self.driver.get_detailed_notes_owned()

        # Separate out notes by status
        current = [note for note in notes if note.is_current()]
        late = [note for note in notes if note.is_late()]
        opened = [note for note in notes if note.is_open()]
        closed = [note for note in notes if not note.is_open()]
        review = [note for note in notes if not note.is_issued()]

        summary = ''
        if late_only:
            summary = '%d late note(s)' % (len(late))
            for note in late:
                summary += '\n%s' % (note)

        else:
            summary_notes = opened
            if include_closed:
                summary_notes += len(closed)
            avg_rate = sum(x['interestRate'] for x in summary_notes) / len(summary_notes)
            summary = '%d note(s) owned at an average interest rate of %.2f%%\n' % (len(summary_notes), avg_rate)
            summary += '%d open note(s):\n' % (len(opened))
            summary += '  %d current note(s)\n' % (len(current))
            if include_closed:
                summary += '  %d closed note(s)\n' % (len(closed))
            summary += '  %d late note(s)\n' % (len(late))
            summary += '  %d note(s) in review\n' % (len(review))
            grade_summary = '  Grades - '
            grades = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
            for grade in grades:
                grade_summary += '%c: %d  ' % (grade, len([n for n in summary_notes if grade in n['grade']]))
            summary += grade_summary

        self.logger.info(summary)
        return summary

    def find_late_notes(self):
        summary = self.note_summary(late_only=True)
        return summary

    def invest(self):
        """Invest in newly listed loans that pass filters."""
        portfolio = self.driver.get_portfolio(lenderbot_get_portfolio(self.config), create=True)
        available_cash = self.driver.get_cash()
        invest_amount = self.config['account']['orderamnt']

        # Find loans that pass filters
        loans = []
        self.logger.info('Retrieving new loans')
        for _ in range(1, 140):
            loans = self.driver.get_loans()
            loans = self.__apply_filters(loans)
            if len(loans):
                break

        # Purchase as many loans as we can
        num_loans = int(min(available_cash/invest_amount, len(loans)))
        purchased_loans = self.driver.submit_order(loans[:num_loans], portfolio)

        # Book keeping
        self.logger.info('%d loan(s) pass filters', len(loans))
        if len(loans) > 0:
            self.logger.info('%d loan(s) succesfully purchased', len(purchased_loans))
        # TODO: Database stuff

    def fund_account(self):
        min_balance = self.config['account']['min_balance']
        transfer_multiple = 25
        cash = self.driver.get_cash()
        if cash >= min_balance:
            return

        # Sum pending transfers amounts
        xfers = self.driver.get_pending_transfers()
        pending_xfer_amt = sum([x['amount'] for x in xfers])

        # Transfer additional funds if cash + pending transfers < min_balance
        total_funds = cash + pending_xfer_amt
        if total_funds < min_balance:
            xfer_amt = ((min_balance - total_funds) + (transfer_multiple - .01)) // transfer_multiple * transfer_multiple
            self.logger.info('Transfering $%d to meet minimum balance requirement of $%d', xfer_amt, min_balance)
            self.driver.add_funds(xfer_amt)

    def test_filters(self):
        """Test filters by applying each one to every currently available loan."""
        self.logger.info('Testing loan filters')
        loans = self.driver.get_loans(showAll=True)
        for f in self.filters:
            self.logger.info('Testing filter: %s', f)
            try:
                for l in loans:
                    f.apply(l)
            except:
                self.logger.error('Filter (%s) FAILED', f)
        self.logger.info('Loan filter testing complete')

