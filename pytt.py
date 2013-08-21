#!/usr/bin/python2.7
import termios,sys,tty,select,unicodedata

class EscapeSequence(Exception):
	pass

class Pytt:
	def __init__(self):
		import sys
		self.stdin		= sys.stdin
		self.stdout		= sys.stdout
		self.buffer		= u''
		self.lastbuffer	= u''
		self.cursor		= 0
		self.mode		= 'insert'
		self.prompt		= u''
		self.selection	= 0
		self.settings = {
			"selection.color": u'\33[7;4m'
		}
		self.colors = {
			"reset": u'\33[0m'
		}
		self.sequences = {
			"\33": {
				"[": {
					"D": "LEFT",
					"C": "RIGHT",
					"H": "HOME",
					"F": "END",
					"3": {
						"~": "DEL"
					},
					"1": {
						";": {
							"1": {
								"0": {
									"D": "SHIFT+ALT+LEFT",
									"C": "SHIFT+ALT+RIGHT"
								}
							},
							"2": {
								"D": "SHIFT+LEFT",
								"C": "SHIFT+RIGHT"
							}
						}
					}
				}
			}
		}

	def head(self):
		return self.buffer[:self.cursor]
	def tail(self):
		return self.buffer[self.cursor:]

	def moveCursor(self, position, selection=0):
		stdout = self.stdout
		buffer = self.buffer
		if self.selection != 0 and selection == 0:
			# Clear selection
			self.selection = 0
			pass

		# Move Right
		if self.cursor < position and self.cursor < len(buffer):
			nchars = position - self.cursor
			stdout.write(buffer[self.cursor:position].encode('UTF-8'))
			self.cursor = position
			return True
		# Move Left
		elif position < self.cursor and self.cursor > 0:
			i = 0
			for char in buffer[position:self.cursor]:
				if i < selection:
					stdout.write( ('\b' + self.settings['selection.color'] + char + u'\33[0m').encode('UTF-8') )
				stdout.write( self.charWidth(char) * '\b' )
				i+=1
			self.cursor = position
			self.selection = selection
			return True
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

	def strWidth(self, s):
		width = 0
		for char in s:
			width += self.charWidth(char)
		return width

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
				if self.selection == 0:
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
				if self.selection > 0:
					selectionstr	= buffer[self.cursor:self.selection]
					tailwidth		= self.strWidth(tail)
					ntail			= tail[self.selection:]
					ntailwidth		= self.strWidth(ntail)
					stdout.write(tailwidth * ' ' + tailwidth * '\b')
					stdout.write(ntail.encode('UTF-8'))
					stdout.write(ntailwidth * '\b')
					self.buffer = head + ntail
			# Escape
			elif c == '\33':
				c = self.stdin.read(1)
				if c == '[':
					c2 = self.stdin.read(1)
					# LEFT
					if c2 == 'D':
						self.moveCursor(self.cursor-1)
					# RIGHT
					elif c2 == 'C':
						self.moveCursor(self.cursor+1)
					# HOME
					elif c2 == 'H':
						self.moveCursor(0)
					# END
					elif c2 == 'F':
						self.moveCursor(len(buffer))
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
							print 'Unknown escape code 3:', repr(c+c2+c3)
					# SELECT
					elif c2 == '1':
						c3 = self.stdin.read(1)
						if c3 == ';':
							c4 = self.stdin.read(1)
							if c4 == '1':
								c5 = self.stdin.read(1)
								if c5 == '0':
									print "Alt+Shift+Left"
								else:
									print repr(c+c2+c3+c4+c5)
							elif c4 == '2':
								c5 = self.stdin.read(1)
								if c5 == 'D':
									# Select Left
									self.moveCursor(self.cursor-1, self.selection+1)
								elif c5 == 'C':
									# Select Right
									self.moveCursor(self.cursor+1, self.selection-1)
								else:
									raise EscapeSequence(c+c2+c3+c4+c5)
							else:
								print 'Unkown selection escape sequence', repr(c+c2+c3+c4)
						else:
							print 'Unknown escape code 3', repr(c+c2+c3)
					else:
						print 'Unknown escape code 2:', repr(c+c2)
				elif c == '\x1b':
					c2 = self.stdin.read(1)
					if c2 == '[':
						c3 = self.stdin.read(1)
						if c3 == 'D':
							# Alt+Left
							wordboundary = self.buffer[:self.cursor].rfind(' ')
							if wordboundary < 0:
								wordboundary = 0
							self.moveCursor(wordboundary)
						elif c3 == 'C':
							# Alt-Right
							wordboundary = self.buffer.find(' ',self.cursor+1)
							if wordboundary < 0:
								wordboundary = len(self.buffer)
							self.moveCursor(wordboundary)
						else:
							print 'Unknown escape code 3:', repr(c+c2+c3)
					else:
						print 'Unknown escape code 2', repr(c+c2)
				else:
					print 'Unkown escape code 1:', repr(c)
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
