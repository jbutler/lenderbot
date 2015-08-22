#!/usr/bin/env python3

class Loan(dict):
	'A simple class to represent a LendingClub loan. This is a wrapper implementing comparison methods to allow sorting.'

	def __init__(self, *args, **kw):
		super(Loan,self).__init__(*args, **kw)
		self.quality = 100

	def __setitem__(self, key, value):
		if key == 'quality':
			self.quality = value
		else:
			super(Loan,self).__setitem__(key, value)
		return
	def __getitem__(self, key):
		if key == 'quality':
			return self.quality
		return super(Loan,self).__getitem__(key)

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

