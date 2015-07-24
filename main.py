#!/usr/bin/env python3

from datetime import datetime
import json
import logging.config
import io
import operator
import os
import shelve
import smtplib
import sys
import traceback

import investor.investor as investor
import investor.loan_filter as loan_filter


# TODO: Figure out a way to make this not suck
# The user email address is in the configuration dictionary. Need a good way to get at that
# from this exception handler
notification_email = ''
def global_exc_handler(type, value, tb):
	# Catch all uncaught exceptions and email the traceback
	exception = io.StringIO()
	traceback.print_exception(type, value, tb, file=exception)
	email_msg = 'Uncaught exception occurred:\n\n' + exception.getvalue()
	send_email(notification_email, 'Auto-Investor uncaught exception', email_msg)
	return sys.__excepthook__(type, value, tb)

def send_email(recipient, subject, email_body):
	sender = 'auto-invest@domain.com'
	message = """From: Auto-Invest <%s>
To: <%s>
Subject: %s
%s""" % (sender, recipient, subject, email_body)

	try:
		s = smtplib.SMTP('localhost')
		s.sendmail(sender, recipient, message)
		logger.info('Notification email sent successfully.')
	except:
		logger.warn('Failed to send notification email.')
	return

def email_purchase_notification(recipient, num_loans, email_body=''):
	return send_email(recipient, str(num_loans) + ' LendingClub Notes Purchased', email_body)

def add_to_db(db_file, loans):
	try:
		db = shelve.open(db_file)
	except:
		logger.error('Failed to open database (%s). It may be corrupt?' % (db_file))
		return
	for loan in loans:
		if str(loan['id']) not in db:
			logger.info('Adding loan %s to database' % loan['id'])
			db[str(loan['id'])] = loan
	db.close()
	return

def init_filters(investor, exclusion_rules):
	# For each rule, create a filter object and add it to the investor
	filters = []
	for rule in exclusion_rules:
		filters.append( loan_filter.loan_filter(rule['key'], rule['op'], rule['comp']) )
	investor.add_filters(filters)

def main():
	config = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'config.json')
	rules = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'rules.json')
	conf = json.load(open(config))
	exclusion_rules = json.load(open(rules))['exclusions']
	db = 'loans.db'

	# Set up global exception handler - set global containing the users email address
	global notification_email
	notification_email = conf['email']
	sys.excepthook = global_exc_handler

	# Create investor object
	i = investor.investor(conf['iid'], conf['auth'])

	# Initialize filters
	init_filters(i, exclusion_rules)

	# Retrieve available cash and any pending transfers
	available_cash = i.get_cash()
	xfers = i.get_pending_transfers()
	pending_xfer_amt = sum(map(lambda x : x['amount'], xfers))

	# Transfer additional funds if we are below the minimum cash balance
	total_funds = available_cash + pending_xfer_amt
	if total_funds < conf['min_balance']:
		xfer_amt = ((conf['min_balance'] - total_funds) + (conf['orderamnt'] - 1)) // conf['orderamnt'] * conf['orderamnt']
		logger.info('Transfering $%d to meet minimum balance requirement of $%d' % (xfer_amt, conf['min_balance']))
		i.add_funds(xfer_amt)
		pending_xfer_amt += xfer_amt

	# Retrieve new loans that pass filters
	logger.info('Retrieving newly posted loans')
	new_loans = i.get_new_loans()
	if not len(new_loans):
		logger.info('No new loans to invest in. Exiting.')
		return

	# Save loans away for characterization later
	logger.info('%s loans pass filters' % (len(new_loans)))
	add_to_db(db, new_loans)

	# Bail out if we don't have enough cash to invest
	if available_cash < conf['orderamnt']:
		logger.warning('Exiting. Not enough cash to invest')
		return

	# Hell yeah, let's order
	#if 'yes' in input('Are you sure you wish to invest in these loans? (yes/no): '):
	num_loans = min( int(available_cash) / conf['orderamnt'], len(new_loans))
	logger.info('Placing order with %s loans.' % (num_loans))
	if i.submit_order(new_loans[0 : num_loans]):
		email_body = 'Purchased %s loan(s) at %s\n\n' % (num_loans, datetime.now())
		for loan in new_loans[0 : num_loans]:
			email_body += '%s\n' % (str(loan))
		email_purchase_notification(conf['email'], num_loans, email_body=email_body)

	return

if __name__ == '__main__':
	# TODO: This is ugly
	log_config = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'logging.json')
	logging.config.dictConfig(json.load(open(log_config, 'rt')))
	logger = logging.getLogger('investor')

	try:
		main()
	except KeyboardInterrupt:
		# Don't email if we manually kill the program
		logger.info('Keyboard interrupt received - killing program')

