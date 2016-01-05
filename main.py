#!/usr/bin/env python3

import argparse
from datetime import datetime
import json
import io
import logging.config
import os
import sys
import traceback

from notify import *
from investor import Investor
from investor import LoanFilter

CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.lenderbot')


def invest(investor, portfolio=None, orderamnt=25):
    # Get loan portfolio
    if portfolio:
        portfolio = investor.get_portfolio(portfolio, create=True)
        if not portfolio:
            logger.error('Could not create portfolio')

    # Get available cash first so we can jump on new loans as soon as they list
    available_cash = investor.get_cash()

    # Find loans meeting filter criteria
    logger.info('Retrieving new loans')
    new_loans = investor.get_new_loans()

    # Log number of loans that pass filters
    if new_loans:
        if len(new_loans) > 1:
            logger.info('%d loans pass filters', len(new_loans))
        else:
            logger.info('1 loan passes filters')
    else:
        logger.info('No new loans pass filters')
        return

    # Purchase as many notes as we can
    num_loans = int(min(available_cash / orderamnt, len(new_loans)))
    if num_loans > 0:
        investor.submit_order(new_loans[0:num_loans], portfolio)
        if num_loans > 1:
            logger.info('Placed order with %s loans', num_loans)
        else:
            logger.info('Placed order with 1 loan')

    # Return only loans we invested in
    return new_loans[:num_loans]


def fund_account(investor, min_balance=0, transfer_multiple=25):
    cash = investor.get_cash()
    if cash >= min_balance:
        return

    # Sum pending transfers amounts
    xfers = investor.get_pending_transfers()
    pending_xfer_amt = sum([x['amount'] for x in xfers])

    # Transfer additional funds if cash + pending transfers < min_balance
    total_funds = cash + pending_xfer_amt
    if total_funds < min_balance:
        xfer_amt = ((min_balance - total_funds) + (transfer_multiple - .01)) // transfer_multiple * transfer_multiple
        logger.info('Transfering $%d to meet minimum balance requirement of $%d', xfer_amt, min_balance)
        investor.add_funds(xfer_amt)


def note_summary(investor, late_only=False, include_closed=False):
    # Get full list of owned notes
    notes = investor.get_detailed_notes_owned()

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

    return summary


def load_filters(rules=os.path.join(CONFIG_DIR, 'rules.json')):
    # Load filter rules from config
    filters = {}
    with open(rules) as rules_file:
        filters = json.load(rules_file)

    # Initialize filters
    filter_objs = []
    if 'basic' in filters:
        logger.info('Adding %s basic filter(s)', len(filters['basic']))
        for rule in filters['basic']:
            filter_objs.append(LoanFilter.BasicFilter(rule['filter']))
    if 'exclusions' in filters:
        logger.info('Adding %s exclusion filter(s)', len(filters['exclusions']))
        for rule in filters['exclusions']:
            filter_objs.append(LoanFilter.ExclusionFilter(rule['filter']))

    return filter_objs


def load_config(config_file=os.path.join(CONFIG_DIR, 'config.json')):
    # Load and validate config
    config = {}
    with open(config_file) as cf_handle:
        config = json.load(cf_handle)

    # Account ID and authentication key are required to do anything useful
    if 'iid' not in config:
        logger.warning('Investor ID not present in config')
    if 'auth' not in config:
        logger.warning('Authentication key not present in config')

    # Assume $25 order amount and $0 minimum balance if either are missing
    if 'orderamnt' not in config:
        logger.info('Setting default order amount to $25')
        config['orderamnt'] = 25
    if 'min_balance' not in config:
        logger.info('Setting default minimum balance to $0')
        config['min_balance'] = 0

    # Email is required for notifications
    if 'email' not in config:
        logger.warning('Email is required to receive notifications')

    return config


def _parse_args():
    parser = argparse.ArgumentParser(description='Autonomous LendingClub account management.')
    parser.add_argument('-a', '--autoMode', action='store_true', help='Enter auto-mode. Check notes, fund account, and invest in available loans.')
    parser.add_argument('-f', '--fundAccount', action='store_true', help='Transfer funds to meet minimum account balance.')
    parser.add_argument('-i', '--invest', action='store_true', help='Invest spare cash in available loans passing filters.')
    parser.add_argument('-l', '--findLate', action='store_true', help='Find notes that are no longer current and notify user.')
    parser.add_argument('-p', '--productionMode', action='store_true', help='Enter production mode. Required to invest or transfer funds.')
    parser.add_argument('-s', '--summarizeNotes', action='store_true', help='Provide status summary of all held notes.')
    parser.add_argument('-t', '--testFilters', action='store_true', help='Test loan filters by applying them to all loans currently listed. Exit once complete.')
    return parser.parse_args()


def _main():
    # First things first. Load the config
    config = load_config()

    try:
        args = _parse_args()
        if args.productionMode:
            logger.warning('Entering production mode. Auto-investor may invest in loans or transfer money into your LendingClub account according to your configuration.')

        # Auto-mode is a set of operations
        if args.autoMode:
            args.findLate = True
            args.fundAccount = True
            args.invest = True

        # Create investor object
        i = Investor.Investor(config['iid'],
                              config['auth'],
                              invest_amt=config['orderamnt'],
                              production_mode=args.productionMode)
        if args.invest or args.testFilters:
            i.add_filters(load_filters())

        if args.summarizeNotes:
            summary = note_summary(i)
            logger.info(summary)
            email_note_summary(config['email'], summary)
        elif args.findLate:
            summary = note_summary(i, late_only=True)
            logger.info(summary)

        if args.invest:
            portfolio_name = None
            if 'portfolio' in config:
                portfolio_name = datetime.now().__format__(config['portfolio'])
            notes = invest(i, portfolio=portfolio_name)
            if notes and 'email' in config:
                email_body = 'Purchased %s loan(s) at %s\n\n' % (len(notes), datetime.now())
                for note in notes:
                    email_body += '%s\n' % (str(note))
                email_purchase_notification(config['email'], len(notes), email_body=email_body)

        if args.fundAccount:
            fund_account(i, config['min_balance'])

        if args.testFilters:
            i.test_filters()

    except KeyboardInterrupt:
        # Don't email if we manually kill the program
        logger.info('Keyboard interrupt received - killing program')

    except SystemExit:
        # Argparse calls sys.exit() when the --help option is given
        pass

    except:
        # Uncaught exception occurred -- log it
        trace_back = sys.exc_info()[2]
        exception_str = io.StringIO()
        traceback.print_tb(trace_back, file=exception_str)
        logger.error('Uncaught exception occurred:\n%s', exception_str.getvalue())
        raise

    return

if __name__ == '__main__':
    log_config = os.path.join(CONFIG_DIR, 'logging.json')
    logging.config.dictConfig(json.load(open(log_config, 'rt')))
    logger = logging.getLogger('investor')

    _main()
