#!/usr/bin/env python3
from email.parser import Parser

class strview(object):
	__slots__ = ('_string', '_start', '_stop')

	def __init__(self, string, start=0, stop=None):
		self._string = str(string)
		self._start  = min(start, len(self._string))
		self._stop   = (min(stop, len(self._string))
		                if stop is not None
		                else len(self._string))

	def __getitem__(self, index):
		if not isinstance(index, slice):
			return self._string[self._start + index.__index__()]
		if index.step is not None:
			raise ValueError('stepping is not supported')
		start = index.start if index.start is not None else 0
		if start < 0 or index.stop is not None and index.stop < 0:
			raise ValueError('negative indices are not supported')
		return type(self)(self._string,
		                  self._start + start,
		                  self._start + index.stop
		                  if index.stop is not None
		                  else self._stop)

	def __str__(self):
		return self._string[self._start:self._stop]

	def __len__(self):
		return (min(self._stop, len(self._string)) -
		        min(self._start, len(self._string)))

LONERS = frozenset('"(),/:;<=>?@[\]{}')
SPACES = frozenset(' \t\r\n()')

def trim(s):
	i, n = 0, 0
	while i < len(s):
		if s[i] == '(':
			n += 1
		elif s[i] == ')':
			n -= 1
			if n < 0:
				raise ValueError('uninitiated comment')
		elif s[i] == '\\':
			i += 1
			if i >= len(s):
				raise ValueError('unterminated quoted-pair')
		elif n == 0 and s[i] not in SPACES:
			break
		i += 1
	else:
		if n > 0:
			raise ValueError('unterminated comment')
	return str(s[:i]), s[i:]

def chop(s):
	assert s
	if s[0] == '"':
		i, b = 1, []
		while i < len(s):
			if s[i] == '"':
				return (''.join(b), *trim(s[i+1:]))
			if s[i] == '\\':
				i += 1
				if i >= len(s):
					raise ValueError('unterminated quoted-pair')
			b.append(s[i])
			i += 1
		else:
			raise ValueError('unterminated string')
	elif s[0] in LONERS:
		return (s[0], *trim(s[1:]))
	else:
		i = 0
		while i < len(s) and s[i] not in LONERS | SPACES:
			i += 1
		return (str(s[:i]), *trim(s[i:]))

def tokenize(s):
	w, s = trim(s)
	yield None, w
	while s:
		t, w, s = chop(s)
		yield t, w

def join(ps):
	return ''.join((t or '') + (' ' if w else '') for t, w in ps)

def parsefields(ps):
	it = iter(ps)
	t, _ = next(ps)
	assert t is None
	return fields(it)

def fields(it):
	terms = [(1, field(it))]
	while True:
		try:
			t, _ = next(it)
		except StopIteration:
			return terms
		if t == '+':
			op = 1
		elif t == '-':
			op = -1
		else:
			raise ValueError('expected an operator')
		terms.append((op, field(it)))

def field(it):
	try:
		t, _ = next(it)
	except StopIteration:
		raise ValueError('expected a field')

	if t == '{':
		end = '}'
		fun = str
	elif t == '[':
		end = ']'
		fun = int
	else:
		raise ValueError('expected a field')

	text = []
	while True:
		try:
			t, w = next(it)
		except StopIteration:
			raise ValueError('unterminated field')
		if t == end:
			break
		text.append((t, w))

	return fun(join(text))

if __name__ == '__main__':
	from sys import stdin
	msg = Parser().parse(stdin, headersonly=True)
	print(parsefields(tokenize(strview(msg['Present']))))
