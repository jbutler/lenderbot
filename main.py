#!/usr/bin/env python

import json
import operator
import shelve
import os

from investor import investor

operators = { ">" : operator.gt, ">=" : operator.ge, "<" : operator.lt, "<=" : operator.le, "==" : operator.eq, "!=" : operator.ne }

def filter(loan, exclusion_rules):
	try:
		for rule in exclusion_rules:
			p = True
			comp = rule['comp']
			if comp == 'None':
				#print("Setting comp to None")
				comp = None

			# Catch the case where the key value should be None but it isn't
			if loan[rule['key']] != None and comp == None:
				return False
			# Toss loans that do not define the key required by the filter
			if loan[rule['key']] == None and comp != None:
				return False

			# Handle normal comparisons
			if not rule['op'] in operators:
				print("ERROR: Unknown operator %s" % rule['op'])
				p = False
			else:
				op = operators[rule['op']]
				p = not op(loan[rule['key']], comp)

			if not p:
				#print("Value (%s) %s %s" % (loan[rule['key']], rule['op'], comp))
				return False
	except:
		print("ERROR parsing filter:")
		print("Rule: %s" % (rule))
		print("Loan: %s" % (loan))
		return False
	return True

def test_add_funds(i, amount):
	i.add_funds(amount)
	return

def add_to_db(db_file, loans):
	db = shelve.open(db_file)
	for loan in loans:
		if str(loan['id']) in db:
			print("Loan %s already present in database" % loan['id'])
		else:
			print("Adding loan %s to database" % loan['id'])
			db[str(loan['id'])] = loan
	db.close()
	return

def main():
	rules = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rules.json')
	cfg_data = json.load(open(rules))
	exclusion_rules = cfg_data['exclusions']
	conf = cfg_data['config']
	db = 'loans.db'

	i = investor(conf['iid'], conf['auth'])
	test_add_funds(i, 1)
	return

    # Retrieve list of loans and and notes that I current own
	new_loans = i.get_new_loans(showAll=True)
	my_note_ids = i.get_my_note_ids()

	# Filter list
	new_loans = [ loan for loan in new_loans if filter(loan, exclusion_rules) ]
	new_loans = [ loan for loan in new_loans if loan['id'] not in my_note_ids ]

	print("Found %s loans to invest in." % (len(new_loans)))
		
	# Bail out if we don't have enough cash to invest
	available_cash = i.get_cash()
	#if available_cash < conf['orderamnt']:
	#	print("Exiting. Not enough cash to invest")
	#	return

	# Fuck yeah, let's order
	i.submit_order(new_loans[0 : min( int(available_cash / conf['orderamnt']), len(new_loans))])

	# Save loans away for characterization later
	add_to_db(db, new_loans)
	
	#print("LendingClub POST Test: Attempting to add 1 dollar")
	#test_add_funds(i, 1)

if __name__ == "__main__":
    main()
