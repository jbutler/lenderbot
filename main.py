#!/usr/bin/env python3

from datetime import datetime
import json
import logging.config
import operator
import os
import shelve
import smtplib
import time

import investor

operators = { ">" : operator.gt, ">=" : operator.ge, "<" : operator.lt, "<=" : operator.le, "==" : operator.eq, "!=" : operator.ne }

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

def email_notification(recipient, num_loans, email_body=""):
	sender = 'auto-invest@domain.com'
	message = """From: Auto-Invest <%s>
To: <%s>
Subject: %s LendingClub Notes Purchased

%s""" % (sender, recipient, num_loans, email_body)

	try:
		s = smtplib.SMTP('localhost')
		s.sendmail(sender, recipient, message)
		logger.info("Notification email sent successfully.")
	except:
		logger.warn("Failed to send notification email.")
	return

def add_to_db(db_file, loans):
	db = shelve.open(db_file)
	for loan in loans:
		if str(loan['id']) not in db:
			logger.info("Adding loan %s to database" % loan['id'])
			db[str(loan['id'])] = loan
	db.close()
	return

def retrieve_and_filter_loans(investor, exclusion_rules):
    # Retrieve list of loans and and notes I current own
	new_loans = investor.get_new_loans(showAll=True)
	my_note_ids = investor.get_my_note_ids()

	# Filter list
	logger.info('Applying filters to %s loans.' % (len(new_loans)))
	new_loans = [ loan for loan in new_loans if filter(loan, exclusion_rules) ]
	new_loans = [ loan for loan in new_loans if loan['id'] not in my_note_ids ]
	return new_loans

def main():
	rules = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rules.json')
	cfg_data = json.load(open(rules))
	exclusion_rules = cfg_data['exclusions']
	conf = cfg_data['config']
	db = 'loans.db'

	i = investor.investor(conf['iid'], conf['auth'])

	# We don't know exactly when loans are going to list, so unfortunately we
	# have to poll. Keep trying for ~5 minutes before giving up. Bail out
	# early if loans post and we invest in something
	for _ in range(120):
		new_loans = retrieve_and_filter_loans(i, exclusion_rules)
		if not len(new_loans):
			logger.info('No new loans pass filters. Exiting')
			time.sleep(1)
			continue

		# Save loans away for characterization later
		logger.info('%s loans pass filters. Adding them to database' % (len(new_loans)))
		add_to_db(db, new_loans)

		# Bail out if we don't have enough cash to invest
		available_cash = i.get_cash()
		if available_cash < conf['orderamnt']:
			logger.warning('Exiting. Not enough cash to invest')
			return

		# Hell yeah, let's order
		#if 'yes' in input('Are you sure you wish to invest in these loans? (yes/no): '):
		num_loans = min( int(available_cash) / conf['orderamnt'], len(new_loans))
		logger.info('Placing order with %s loans.' % (num_loans))
		if i.submit_order(new_loans[0 : num_loans]):
			email_notification(conf['email'], num_loans, email_body="Purchased %s loans at %s"%(num_loans, datetime.now()))
			return

	return

if __name__ == "__main__":
	# TODO: This is ugly
	log_config = 'logging.json'
	logging.config.dictConfig(json.load(open(log_config, 'rt')))
	logger = logging.getLogger('investor')

	main()

