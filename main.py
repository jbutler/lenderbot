#!/usr/bin/env python3

import argparse
from datetime import datetime
import json
import logging.config
import os

from notify import *
from investor import Investor
from investor import LoanFilter


def invest(investor, portfolio=None, orderamnt=25):
	# Get loan portfolio
	p = None
	if portfolio:
		p = investor.get_portfolio(portfolio)
		if not p:
			logger.error('Could not create portfolio (%s)' % (portfolio))

	# Find loans meeting filter criteria
	logger.info('Retrieving new loans')
	new_loans = investor.get_new_loans()

	# Purchase as many notes as we can
	num_loans = int(min(investor.get_cash() / orderamnt, len(new_loans)))
	if num_loans > 0:
		logger.info('Placing order with %s loans.' % (num_loans))
		investor.submit_order(new_loans[0:num_loans], p)
	else:
		logger.info('No new loans pass filters.')

	# Return only loans we invested in
	return new_loans[:num_loans]


def fund_account(investor, min_balance=0, transfer_multiple=25):
	cash = investor.get_cash()
	if cash >= min_balance:
		logger.info('Current account balance: $%d' % (cash))
		return

	# Sum pending transfers amounts
	xfers = investor.get_pending_transfers()
	pending_xfer_amt = sum([ x['amount'] for x in xfers ])

	# Transfer additional funds if cash + pending transfers < min_balance
	total_funds = cash + pending_xfer_amt
	if total_funds < min_balance:
		xfer_amt = ((min_balance - total_funds) + (transfer_multiple - .01)) // transfer_multiple * transfer_multiple
		logger.info('Transfering $%d to meet minimum balance requirement of $%d' % (xfer_amt, min_balance))
		investor.add_funds(xfer_amt)


def note_summary(investor, late_only=False):
	logger.info('Note summary here')
	return


def load_filters(rules=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'rules.json')):
	# Load filter rules from config
	filters = {}
	with open(rules) as f:
		filters = json.load(f)

	# Initialize filters
	filter_objs = []
	if 'basic' in filters:
		logger.info('Adding %s basic filter(s)' % (len(filters['basic'])))
		for rule in filters['basic']:
			filter_objs.append(LoanFilter.BasicFilter(rule['filter']))
	if 'exclusions' in filters:
		logger.info('Adding %s exclusion filter(s)' % (len(filters['exclusions'])))
		for rule in filters['exclusions']:
			filter_objs.append(LoanFilter.ExclusionFilter(rule['filter']))

	return filter_objs


def load_config(config_file=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'config.json')):
	# Load and validate config
	config = {}
	with open(config_file) as f:
		config = json.load(f)

	# Account ID and authentication key are required to do anything useful
	if not 'iid' in config:
		logger.warning('Investor ID not present in config')
	if not 'auth' in config:
		logger.warning('Authentication key not present in config')

	# Assume $25 order amount and $0 minimum balance if either are missing
	if not 'orderamnt' in config:
		logger.info('Setting default order amount to $25')
		config['orderamnt'] = 25
	if not 'min_balance' in config:
		logger.info('Setting default minimum balance to $0')
		config['min_balance'] = 0

	# Email is required for notifications
	if not 'email' in config:
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
		i = Investor.Investor(config['iid'], config['auth'], productionMode=args.productionMode)
		if args.invest or args.testFilters:
			i.add_filters(load_filters())

		if args.summarizeNotes:
			summary = note_summary(i)
		elif args.findLate:
			summary = note_summary(i, late_only=True)

		if args.fundAccount:
			fund_account(i, config['min_balance'])

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

		if args.testFilters:
			i.test_filters()

	except KeyboardInterrupt:
		# Don't email if we manually kill the program
		logger.info('Keyboard interrupt received - killing program')

	except:
		# Send email notification about uncaught exception
		logger.error('Uncaught exception occurred.')

		# TODO: Send email with backtrace

		raise

	return

if __name__ == '__main__':
	# TODO: This is ugly
	log_config = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'logging.json')
	logging.config.dictConfig(json.load(open(log_config, 'rt')))
	logger = logging.getLogger('investor')

	_main()

