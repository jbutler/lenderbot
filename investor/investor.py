#!/usr/bin/env python3

import datetime
import json
import requests
import logging
import time

# investor imports
from investor import loan_filter


class loan(dict):
	'A simple class to represent a LendingClub loan. This is a wrapper implementing comparison methods to allow sorting'

	def __init__(self, *args, **kw):
		super(loan,self).__init__(*args, **kw)
		self.quality = 100

	def __setitem__(self, key, value):
		if key == 'quality':
			self.quality = value
		else:
			super(loan,self).__setitem__(key, value)
		return
	def __getitem__(self, key):
		if key == 'quality':
			return self.quality
		return super(loan,self).__getitem__(key)

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

	def __repr__(self):
		# Print some of the more interesting loan details
		str  = 'Loan ID: %s\n' % (self['id'])
		str += 'Amount Requested: $%d\n' % (self['loanAmount'])
		str += 'Loan purpose: %s\n' % (self['purpose'])
		str += 'Loan grade: %s\n' % (self['subGrade'])
		str += 'Interest rate: %.2f\n' % (self['intRate'])
		str += 'Loan length: %d months\n' % (self['term'])
		str += 'Monthly payment: $%d\n' % (self['installment'])
		return str


class investor:
	'A simple class to interact with your LendingClub account'

	def __init__(self, iid, authKey, investAmt=25, productionMode=False):
		self.iid = iid
		self.headers = { 'Authorization' : authKey, 'Accept' : 'application/json', 'Content-type' : 'application/json' }
		self.investAmt = investAmt
		self.productionMode = productionMode
		self.logger = logging.getLogger(__name__)
		self.time_delay = datetime.timedelta(seconds=1) # We must wait one second between requests
		self.last_request_ts = datetime.datetime.now()
		self.filters = []
		self.my_note_ids = self.get_my_note_ids()

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

	def __execute_get(self, url):
		self.__execute_delay()
		response = requests.get(url, headers=self.headers)
		self.__set_ts()
		if not response:
			self.logger.error('Error occurred during GET: %s\n  HTTP response: %s' % (url, response.status_code))
		return response.text

	def __execute_post(self, url, payload=None):
		self.__execute_delay()
		response = requests.post(url, data=payload, headers=self.headers)
		self.__set_ts()
		if not response:
			self.logger.error('Error occurred during POST: %s\n  HTTP response: %s' % (url, response.status_code))
		return response.text

	def __apply_filters(self, loans):
		# First, filter out loans we already own
		num_loans = len(loans)
		loans = [ loan for loan in loans if loan['id'] not in self.my_note_ids ]
		if num_loans != len(loans):
			self.logger.info('Filtering out loan(s) already invested in')

		# Second, apply user defined filters
		for f in self.filters:
			loans = [ loan for loan in loans if f.apply(loan) ]
		return loans

	def add_filters(self, filters):
		for f in filters:
			self.filters.append(f)

	def get_cash(self):
		cash = self.__execute_get('https://api.lendingclub.com/api/investor/v1/accounts/%s/availablecash' % (self.iid))
		if not cash:
			return 0
		return json.loads(cash)['availableCash']

	def get_new_loans(self, showAll=False):
		for _ in range(1,140):
			loans = None
			listings_json = self.__execute_get('https://api.lendingclub.com/api/investor/v1/loans/listing?showAll=%s' % (showAll))
			try:
				raw_loans = json.loads(listings_json)['loans']
				loans = [ loan(raw_loan) for raw_loan in raw_loans ]
			except:
				# Key error, most likely
				self.logger.warning('Loan retrieval failed. Response text:\n  -- %s' % (listings_json))
				continue
			loans = self.__apply_filters(loans)
			if len(loans):
				self.logger.info('%d loan(s) pass filters' % len(loans))
				return loans

		self.logger.info('No loans pass filters.')
		return []

	def get_my_note_ids(self):
		mynotes_json = self.__execute_get('https://api.lendingclub.com/api/investor/v1/accounts/%s/notes' % (self.iid))
		return [ x['loanId'] for x in json.loads(mynotes_json)['myNotes'] ]

	def submit_order(self, loans):
		if self.productionMode:
			loan_dict = [ { 'loanId' : loan['id'], 'requestedAmount' : self.investAmt } for loan in loans ]
			order = json.dumps({ "aid" : self.iid, "orders" : loan_dict })
			return self.__execute_post('https://api.lendingclub.com/api/investor/v1/accounts/%s/orders' % (self.iid), payload=order)
		else:
			self.logger.info('Running in test mode. Skipping loan order')
			return None

	def add_funds(self, amount):
		if self.productionMode:
			payload = json.dumps({ 'amount' : amount, 'transferFrequency' : 'LOAD_NOW' })
			return self.__execute_post('https://api.lendingclub.com/api/investor/v1/accounts/%s/funds/add' % (self.iid), payload=payload)
		else:
			self.logger.info('Running in test mode. Skipping money transfer.')
			return None

	def get_pending_transfers(self):
		xfers = json.loads(self.__execute_get('https://api.lendingclub.com/api/investor/v1/accounts/%s/funds/pending' % (self.iid)))
		if 'transfers' in xfers:
			return xfers['transfers']
		else:
			return []

