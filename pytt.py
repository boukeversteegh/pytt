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
			"\1":	"HOME",
			"\4":	"EOF",
			"\5":	"END",
			"\n":	"RETURN",
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
									"D": "SELECT_WORD_LEFT",
									"C": "SELECT_WORD_RIGHT"
								}
							},
							"2": {
								"D": "SELECT_LEFT",
								"C": "SELECT_RIGHT"
							}
						}
					}
				},
				"\33": {
					"[": {
						"D":	"WORD_LEFT",
						"C":	"WORD_RIGHT"
					}
				}
			},
			"\x7f":	"BACKSPACE"
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
			if self.selection > 0:
				seltail = self.buffer[self.cursor:self.cursor+self.selection]
				for char in seltail:
					stdout.write(char)
				for char in seltail:
					stdout.write('\b'*self.charWidth(char))
			if self.selection < 0:
				selhead = self.buffer[self.cursor+self.selection:self.cursor]
				for char in selhead:
					stdout.write('\b'*self.charWidth(char))
				for char in selhead:
					stdout.write(char)
			self.selection = 0
			pass

		# Don't move
		if self.cursor == position and selection == 0:
			return True
		# Move Right
		elif self.cursor < position and self.cursor < len(buffer):
			if selection < 0: #== self.cursor - position:
				stdout.write(self.settings['selection.color'])
			stdout.write(buffer[self.cursor:position].encode('UTF-8'))
			if selection < 0:# == self.cursor - position:
				stdout.write('\33[0m')
			self.cursor = position
			self.selection = selection
			return True
		# Move Left
		elif position < self.cursor and self.cursor > 0:
			stdout.write(self.strWidth(self.buffer[position:self.cursor])*'\b')
			
			if selection > 0:
				stdout.write( self.settings['selection.color'] )
				selstr = self.buffer[position:self.cursor]
				#stdout.write( self.strWidth(selstr) * '\b' )
				stdout.write( selstr.encode('UTF-8'))
				stdout.write( self.strWidth(selstr) * '\b' )
				stdout.write( '\33[0m' )
			#i = 0
			#for char in buffer[position:self.cursor]:
			#	#if i < selection:
			#		stdout.write( ('\b' + self.settings['selection.color'] + char + u'\33[0m').encode('UTF-8') )
			#	stdout.write( char )
			#	i+=1
			#stdout.write( self.strWidth())
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

	def wordLeft(self, cursor):
		wordboundary = max(0, self.buffer[:self.cursor-1].rfind(' ')+1)
		return wordboundary

	def wordRight(self, cursor):
		wordboundary = self.buffer.find(' ', self.cursor+1)
		if wordboundary < 0:
			wordboundary = len(self.buffer)
		else:
			wordboundary += 1
		return wordboundary
				

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
			# Escape
			elif c in self.sequences:
				s = c
				sequence = self.sequences
				while c in sequence:
					sequence = sequence[c]
					if type(sequence) == dict:
						c = self.stdin.read(1)
						s += c
					else:
						break
				if type(sequence) == dict:
					print 'Unknown sequence: ', repr(s)
				else:
					if sequence == 'LEFT':
						self.moveCursor(self.cursor-1)
					elif sequence == 'RIGHT':
						self.moveCursor(self.cursor+1)
					elif sequence == 'HOME':
						self.moveCursor(0)
					elif sequence == 'END':
						self.moveCursor(len(buffer))
					elif sequence == 'EOF':
						return self.buffer
					elif sequence == 'RETURN':
						if singleline:
							break
						else:
							self.buffer += "\n"
							stdout.write("\n")
					elif sequence == 'DEL':
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
					elif sequence == 'SELECT_LEFT':
						self.moveCursor(self.cursor-1, self.selection+1)
					elif sequence == 'SELECT_RIGHT':
						self.moveCursor(self.cursor+1, self.selection-1)
					elif sequence == 'WORD_LEFT':
						wordboundary = self.wordLeft(self.cursor)
						self.moveCursor(wordboundary)
					elif sequence == 'WORD_RIGHT':
						wordboundary = self.wordRight(self.cursor)
						self.moveCursor(wordboundary)
					elif sequence == 'SELECT_WORD_LEFT':
						wordboundary = self.wordLeft(self.cursor) 
						self.moveCursor(wordboundary, self.cursor+self.selection-wordboundary)
					elif sequence == 'SELECT_WORD_RIGHT':	
						wordboundary = self.wordRight(self.cursor)
						self.moveCursor(wordboundary, wordboundary - self.cursor)
					elif sequence == 'BACKSPACE':
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
						else:
							if self.selection < 0:
								selectionstr = self.buffer[self.cursor+self.selection:self.cursor]
								#stdout.write(self.strWidth(selectionstr)*'\b')
								head = self.buffer[:self.cursor+self.selection]
								tailwidth = self.strWidth(self.buffer[self.cursor:])
								selwidth = self.strWidth(selectionstr)
								stdout.write(tailwidth * ' ' + (selwidth+tailwidth) * '\b' + selwidth * ' ' + selwidth * '\b')
								ntail = tail
								self.cursor = self.cursor+self.selection
							else:
								selectionstr	= buffer[self.cursor:self.cursor+self.selection]
								tailwidth		= self.strWidth(tail)
								ntail			= tail[self.selection:]
								stdout.write(tailwidth * ' ' + tailwidth * '\b')
							ntailwidth		= self.strWidth(ntail)
							stdout.write(ntail.encode('UTF-8'))
							stdout.write(ntailwidth * '\b')
							self.buffer = head + ntail
							self.selection = 0
					else:
						print 'Unimplemented:', repr(sequence)
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
			else:
				stdout.write(tail.encode('UTF-8')+' ')
				print '\033[31mNon Printable\033[0m:', n, repr(c), repr(self.buffer), '@',self.cursor
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
