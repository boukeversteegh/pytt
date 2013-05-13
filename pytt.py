#!/usr/bin/python2.7
import termios,sys,tty,select,unicodedata


class Pytt:
	def __init__(self):
		import sys
		self.stdin	= sys.stdin
		self.stdout	= sys.stdout
		self.buffer	= u''
		self.lastbuffer	= u''
		self.cursor	= 0
		self.mode	= 'insert'
		self.prompt	= u''

	def head(self):
		return self.buffer[:self.cursor]
	def tail(self):
		return self.buffer[self.cursor:]

	def moveCursor(self, position):
		stdout = self.stdout
		buffer = self.buffer
		# Move Right
		if self.cursor < position and self.cursor < len(buffer):
			nchars = position - self.cursor
			stdout.write(buffer[self.cursor:position].encode('UTF-8'))
			self.cursor = position
		# Move Left
		elif position < self.cursor and self.cursor > 0:
			for char in buffer[position:self.cursor]:
				stdout.write( self.charWidth(char) * '\b' )
			self.cursor = position
		else:
			stdout.write('\7')
	def insert(self, string, position=None):
		if position is None:
			position = self.cursor
		self.buffer = self.buffer[:position] + string + self.buffer[position:]
		self.cursor += len(string)

	def charWidth(self, char):
		width = unicodedata.east_asian_width(char)
		context = 'normal'
		if width == 'A':
			if context == 'asian':
				return 2
			elif context == 'normal':
				return 1
			else:
				raise Exception("Ambiguous character width, without context")

		if width in ['Na','N']:
			return 1
		elif width in ['W', 'F']:
			return 2
		else:
			raise Exception("Unknown Character Width")

	def _initterm(self):
		self.termbackup = termios.tcgetattr(sys.stdin)
		tty.setcbreak(sys.stdin.fileno())

	def _resetterm(self):
		termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.termbackup)

	def readline(self, prompt=None):
		try:
			return self._read(True, prompt)
		except (Exception, KeyboardInterrupt):
			self._resetterm()
			raise

	def _read(self, singleline=False, prompt=None):
		self.buffer = u''
		self.cursor = 0
		self._initterm()
		stdout = self.stdout
		stdin = self.stdin
		state = None

		if prompt:
			stdout.write(prompt)
			self.prompt = prompt
		
		while True:
			buffer = self.buffer
			head = self.head()
			tail = self.tail()

			c = self.stdin.read(1)
			n = ord(c)
			# Printable
			if 0x20 <= n and n <= 0x7E:
				self.buffer = head + c + tail
				stdout.write(c + tail.encode('UTF-8'))
				for char in tail:
					stdout.write(self.charWidth(char)*'\b')
				self.cursor+=1
			# Backspace
			elif n == 127:
				if self.cursor > 0:
					delwidth = self.charWidth(head[-1])
					stdout.write(delwidth*'\b') # Move cursor back
					stdout.write(tail.encode('UTF-8')) # Rewrite tail
					lastwidth = self.charWidth(buffer[-1])
					stdout.write(lastwidth*' ') # Write space at end
					stdout.write(lastwidth*'\b')
					
					for char in tail:
						width = self.charWidth(char)
						stdout.write(width*'\b')
				
					self.buffer = head[:-1] + tail
					self.cursor-=1
				else:
					stdout.write('\7')
			# Escape
			elif n == 27:
				c = self.stdin.read(1)
				if c == '[':
					c2 = self.stdin.read(1)
					# LEFT
					if c2 == 'D':
						self.moveCursor(self.cursor-1)
						state = None
					# RIGHT
					elif c2 == 'C':
						self.moveCursor(self.cursor+1)
						state = None
					# HOME
					elif c2 == 'H':
						self.moveCursor(0)
						state = None
					# END
					elif c2 == 'F':
						self.moveCursor(len(buffer))
						state = None
					# EXTRA ESCAPE
					elif c2 == '3':
						c3 = self.stdin.read(1)
						# DEL
						if c3 == '~':
							if self.cursor < len(buffer):
								stdout.write(tail[1:])
								lastwidth = self.charWidth(tail[-1])
								stdout.write(lastwidth*' ')
								stdout.write(lastwidth*'\b')
								for char in tail[1:]:
									stdout.write(self.charWidth(char)*'\b')
							else:
								stdout.write('\7')
							self.buffer = head + tail[1:]
						else:
							print 'Unknown escape code:', c+c2+c3
					# SELECT
					else:
						print 'Unknown escape code:', c+c2
						state = None
				else:
					print 'Unkown escape code:', c
			# Home CTRL-A
			elif n == 1:
				self.moveCursor(0)
			# End CTRL-E
			elif n == 5:
				self.moveCursor(len(buffer))
			# EOF CTRL-D
			elif n == 4:
				return buffer
			# UTF8
			elif n > 127:
				
				def getmbchar():
					# Double Byte
					c2 = stdin.read(1)
					if ord(c) & 32 == 0:
						return c+c2
	
					# Triple Byte
					c3 = stdin.read(1)
					if ord(c) & 16 == 0:
						return c+c2+c3
					
					# Quadruple Byte
					c4 = stdin.read(1)
					if ord(c) & 8 == 0:
						return c+c2+c3+c4
				mbchar = getmbchar()
				if mbchar is None:
					stdout.write('\033[7m?\033[7m')
				else:
					#stdout.write('\033[7m' + mbchar + '\033[0m')
					stdout.write(mbchar)
					stdout.write(tail.encode('UTF-8'))
					for char in tail:
						stdout.write(self.charWidth(char)*'\b')
					self.insert(mbchar.decode('UTF-8'))
			# ENTER
			elif n == 10:
				if singleline:
					break
				else:
					self.buffer += "\n"
					stdout.write("\n")
			else:
				stdout.write(tail.encode('UTF-8')+' ')
				print '\033[31mNon Printable\033[0m:', n, repr(self.buffer), '@',self.cursor
				stdout.write(self.buffer.encode('UTF-8'))
				for char in tail:
					width = self.charWidth(char)
					stdout.write(width*'\b')
		
		self._resetterm()
		self.lastbuffer = buffer
		self.buffer = u''
		self.prompt = u''
		return buffer

	def clear(self):
		if self.prompt:
			prompt = self.prompt
		else:
			prompt = u''
		sys.stdout.write('\r' + (' ' * (len(prompt)+len(self.lastbuffer))) + '\r')

pytt = Pytt()
readline	= pytt.readline
clear		= pytt.clear
del pytt

if __name__ == "__main__":
	readline("Name: ")
	clear()
