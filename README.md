pytt
====

**Description**

Interactive user input for Python (replacement for `input_raw`).


Keywords: _TTY, readline, line editing, user input_

**Features**
- UTF-8 support (including proper displaying of Asian double-width characters)
- Backspace, Delete, Inserting text
- Moving the cursor
  - Using left/right arrow keys
  - CTRL+A, CTRL+E to go to Start en End of line (as in Emacs)
  - HOME and END

**Missing Features**
- Windows support
- Some other shortcuts like ctrl+left to jump word by word
- Multiline editing
- Autocompletion

**Example**

```python
import pytt
name = pytt.readline("Enter your name: ")
pytt.clear() # Clear prompt and user input from the screen
print "Hello %s!" % name
```
