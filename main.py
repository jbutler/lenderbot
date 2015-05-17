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

import investor

operators = { '>' : operator.gt, '>=' : operator.ge, '<' : operator.lt, '<=' : operator.le, '==' : operator.eq, '!=' : operator.ne }

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

def filter(loan, exclusion_rules):
	try:
		for rule in exclusion_rules:
			p = True
			comp = rule['comp']
			if comp == 'None':
				comp = None

			# Catch the case where the key value should be None but it isn't
			if loan[rule['key']] != None and comp == None:
				return False
			# Toss loans that do not define the key required by the filter
			if loan[rule['key']] == None and comp != None:
				return False

			# Handle normal comparisons
			if not rule['op'] in operators:
				logger.warn('Unknown operator %s' % (rule['op']))
				p = False
			else:
				op = operators[rule['op']]
				p = not op(loan[rule['key']], comp)

			if not p:
				logger.debug('Value (%s) %s %s' % (loan[rule['key']], rule['op'], comp))
				return False
	except:
		logger.error('Error parsing filter:\nRule: %s\nLoan: %s' % (rule, loan), exc_info=True)
		return False
	return True

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

def retrieve_and_filter_loans(investor, exclusion_rules):
    # Retrieve list of loans and and notes I current own
	new_loans = investor.get_new_loans()
	my_note_ids = investor.get_my_note_ids()

	# Filter list
	new_loans = [ loan for loan in new_loans if filter(loan, exclusion_rules) ]
	new_loans = [ loan for loan in new_loans if loan['id'] not in my_note_ids ]
	return new_loans

def main():
	rules = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'rules.json')
	cfg_data = json.load(open(rules))
	exclusion_rules = cfg_data['exclusions']
	conf = cfg_data['config']
	db = 'loans.db'

	# Set up global exception handler - set global containing the users email address
	global notification_email
	notification_email = conf['email']
	sys.excepthook = global_exc_handler

	# Create investor object
	i = investor.investor(conf['iid'], conf['auth'])

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

	# We don't know exactly when loans are going to list, so unfortunately we
	# have to poll. Keep trying for ~5 minutes before giving up. Bail out
	# early if loans post and we invest in something
	logger.info('Retrieving newly posted loans')
	for _ in range(140):
		new_loans = retrieve_and_filter_loans(i, exclusion_rules)
		if not len(new_loans):
			continue

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

	logger.info('No new loans to invest in. Exiting.')
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

