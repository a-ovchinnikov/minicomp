from collections import deque
import ctypes
import curses
from functools import partial
from itertools import cycle, chain, repeat, islice, takewhile, dropwhile
import os
import sys

from cpu import CPU
from mmu import *
from decorators import *
from utils import *


NotEnoughArgs = TypeError
BASEADDR = 0xe000


def attribute_of_subattribute(obj, attribute, subattribute, sentinel=None):
    if sentinel is None:
        return getattr(getattr(obj, attribute), subattribute)
    return getattr(getattr(obj, attribute), subattribute, sentinel)


def attribute_has_attribute(obj, attr, subattr):
    sentinel = object()
    return attribute_of_subattribute(obj, attr, subattr, sentinel) is not sentinel


def get_help_string(obj, attr):
    return attribute_of_subattribute(obj, attr, help_reg_attr)


def has_help_string(obj, attr):
    return attribute_has_attribute(obj, attr, help_reg_attr)


class Cstr(str):
    def __new__(cls, value, attr=None):
        obj = str.__new__(cls, value)
        obj.curses_attribute = attr
        return obj

    def setcolor(self, color):
        self.curses_attribute = color

    @staticmethod
    def join(separator="", iterable=""):
        return list(islice(chain.from_iterable(zip(repeat(separator), iterable)), 1, None))

    def __iter__(self):
        for el in self.__str__():
            yield Cstr(el, self.curses_attribute)


class Console:
    def __init__(self):
        if getattr(self, "win", None) is None:
            raise TypeError(f"{self.__class__.__name__} must have 'win' property set")
        self.win.scrollok(True)  # no need to mess with a buffer!
        self.current_line = []

    def process_key(self, key):
        if is_return(key):
            self.process_return()
        else:
            self.push_char(key)

    def push_chars(self, chars):
        for ch in chars:
            for subch in ch:  # a hack around Cstr
                self.push_char(subch)

    def push_char(self, char):
        for subch in char:  # a hack around Cstr
            self.current_line.append(subch)
            quux = getattr(subch, "curses_attribute", None)
            if quux is None:
                try:
                    self.win.addch(subch)
                except TypeError:
                    raise Exception(f"Failed on '{char}' {len(char)} {type(char)}")
            else:
                self.win.addch(subch, quux)
        self.win.refresh()

    def activate(self):
        pass

    def deactivate(self):
        pass


class IOWin(Console):
    def __init__(self, nlines=8, char_per_line=50):
        self.nlines = nlines
        self.char_per_line = char_per_line
        self.height = nlines + 2
        self.width = char_per_line + 2
        self.str_buffer = deque([], 8)
        # An extra box to keep the lovely surrounding box and have a hassle-free scrolling
        self.box = curses.newwin(self.height, self.width, 0, 0)
        self.box.border()
        self.box.refresh()
        self.win = curses.newwin(self.nlines, self.char_per_line, 1, 1)
        super(IOWin, self).__init__()
        self.win.refresh()

    def activate(self):
        curses.curs_set(0)
        self.box.addstr(9,44, "-Active")
        self.box.refresh()
        self.win.refresh()

    def deactivate(self):
        self.box.addstr(9,44, "-------")
        self.box.refresh()
        self.win.refresh()
        curses.curs_set(1)

    # IOWindow just passes newline through to the underlying system.
    # It is up to the system how it will deal with it.
    def process_return(self):
        self.push_char("\n")

    # IOWindow just passes backspace through to the underlying system.
    # It is up to the system how it will deal with it.
    def process_backspace(self):
        self.push_char("\b")

    # This is to emulate MemoryIO
    def write(self, value):
        self.push_char(chr(value))

    def read(self, *a):
        pass


class Stats:
    def __init__(self):
        self.win = curses.newwin(10, 8, 0, 52)
        self.reset()

    def reset(self):
        self.count = 0
        self.win.addstr(0, 0, f"PC {hex(BASEADDR)[2:]}")
        self.win.addstr(1, 0, "Sp 0000")  # ??
        self.win.addstr(2, 0, "A 00")
        self.win.addstr(3, 0, "X 00")
        self.win.addstr(4, 0, "Y 00")
        self.win.addstr(5, 0, "N . V .")
        self.win.addstr(6, 0, "B . D .")
        self.win.addstr(7, 0, "I . C .")
        self.win.addstr(8, 0, "Z 1    ")
        self.win.addstr(9, 0, "0")
        self.win.refresh()

    def update_stats(self, cpu, refresh=False):
        """Updates individual field"""
        self.count += cpu.cc
        if refresh:
            self.win.addstr(0, 0, f"PC {word(cpu.r.pc)}")
            self.win.addstr(1, 0, f"Sp {word(cpu.r.s)}")
            self.win.addstr(2, 0, f"A {byte(cpu.r.a)}")
            self.win.addstr(3, 0, f"X {byte(cpu.r.x)}")
            self.win.addstr(4, 0, f"Y {byte(cpu.r.y)}")
            self.win.addstr(5, 0, f"N {'1' if cpu.r.getFlag('N') else '.'} V .")
            self.win.addstr(6, 0, "B . D .")
            self.win.addstr(7, 0, "I 1 C .")
            self.win.addstr(8, 0, f"Z {'1' if cpu.r.getFlag('Z') else '.'}   ")
            self.win.addstr(9, 0, f"{self.count}")
            self.win.refresh()

class CmdProcessor:
    history_len = 500

    def __init__(self, screen, cpumonitor):
        self.screen = screen
        self.cpumonitor = cpumonitor
        self.kdb = Keyboard("Hello, World!!!")
        self.reset_computer(fname=os.path.join(os.path.dirname(__file__), "echo.bin"))
        self.lastcmds = deque(maxlen=self.history_len)
        self._history_pos = -1
        self.helps = dict((el, get_help_string(self, el))
                           for el in filter(partial(has_help_string, self), dir(self)))

    @property
    def history_pos(self):
        return self._history_pos

    @history_pos.setter
    def history_pos(self, value):
        if abs(value) >= self.history_len or abs(value) >= len(self.lastcmds) or value > -1:
            return
        self._history_pos = value

    @property
    def lastcmd(self):
        if self.lastcmds:
            return self.lastcmds[-1]
        return ""

    @lastcmd.setter
    def lastcmd(self, val):
        # No need to append same stuff many times
        if self.lastcmds and val != self.lastcmds[-1]:
            self.lastcmds.append(val)
            self.history_pos = -1
        elif not self.lastcmds:
            self.lastcmds.append(val)
            self.history_pos = -1

    def reset_computer(self, fname=None):
        # RAM(0x00, 0xdbff), everything in 0xdc00:0xdffe is for IO
        # TODO: will eventually need a character device to emulate storage.
        #       and that would require a system config.
        #       Such device would need a backing file and some commands.
        #       Maybe lift these commands from an SPI EEPROM?
        #         READ ADDR:24        -- read byte from ADDR:24
        #         RCONT               -- read next byte after the last ADDR
        #         WRITE ADDR:24 VAL:8 -- write VAL:8 at ADDR:24
        #         WCONT VAL:8         -- write VAL:8 after the last ADDR
        #         STORE               -- saves data to file ???
        if fname is not None:
            self.fname = fname
        with open(self.fname, "rb") as f:
            m = MMU(RAM(0x00, 0x1000), ROM(BASEADDR, 0x10000 - BASEADDR, f))
        m.register_io(1024, self.screen.write)  # register specific method
        m.register_io(1025, self.kdb, "r")
        self.c = CPU(m, BASEADDR, observer=self.cpumonitor)
        self.kdb.reset()

    @register_help("Execute one (default) or more instructions")
    @morph("numstep", to_int, "E: invalid number of steps")
    @precondition("numstep < 10**6", "E: too many steps")
    @precondition("numstep > 0", "E: cannot make less than one step")
    def step(self, numstep=1):
        for _ in range(numstep - 1):
            self.c.step()
        self.c.step(refresh=True)
        return ""

    @register_help("Add everything that follows verbatim to keyboard device")
    def addinpt(self, *a):
        # TODO: make this work with 0x10 0x77 etc. to provide actual hex codes.
        # TODO: add <fname operator
        # TODO: add escape characters for 0x10 or even better:
        #       addinptraw 0x10  would result in 0x10 echoed to the screen
        if a:
            for el in a:
                self.kdb.extend(el.replace("\\n", "\n"))
        return ""

    @register_help("Execute commands from /file/")
    @missing_args("E: missing filename")
    @precondition("file_accessible(fname)", "E: cannot read file")
    def exefile(self, fname):
        out = []
        try:
            with open(fname, "r") as f:
                for line in f.readlines():
                    out.append("..>"+line.rstrip())
                    self.process(line.rstrip().split(" ", 1), update_last_command=False)
        except Exception as e:
            out.append("E: "+ str(e))
        return "\n".join(out)

    @register_help("Show memory surrounding /addr/ /as hex/ or /as ascii/")
    @missing_args("E: missing address")
    @morph("addr", substitute_pc, "IE: should never result in error")
    @morph("addr", to_int, "E: not a number")
    @precondition("0x0000 <= addr <= 0xffff", "E: impossible address")
    def ctxt(self, addr, mod1="as", mod2="hex"):
        # Cannot overflow over 0xffff or underflow below 0:
        # Note, that to see _current address_ and two extra lines it must be
        # + 15.
        tmph, tmpl = addr + 15, addr -8
        hi, lo = min(addr + 15, 0xffff), max(addr - 8, 0)
        # Note: dump does NOT recenter by itself!
        asascii, output = mod1 == "as" and mod2 == "ascii", ["--"] * abs(tmpl) if tmpl < 0 else []
        # -- repreasents values outside of address range.
        for i in range(lo, hi + 1):
            if i in self.c.mmu.ioread:
                val = byte_to_repr(self.c.mmu.ioread[i].peek(), asascii)
                val = Cstr(val, curses.color_pair(100))
            else:
                val = mem_element(self.c.mmu, i, asascii)
            output.append(val)
        if tmph > 0xffff:
            output.extend(["--"] * (tmph - 0xffff))
        # Formatting the table:
        # This code is a mess and requires lots more comments
        # And it should still be a part of the dumper, but the dumper has to be smart
        # enough to deal with context-aware and context-less ranges.
        tbl_width = 8
        diap = enumerate(range(0, len(output), 8), -1 if tmpl < 0 else 0)
        if tmpl < 0:
            addr = lambda ofs: word(lo + 8*ofs + 8 - abs(tmpl)) + "  " if tmpl > 0 or ofs >= 0 else "----  "
        elif tmph > 0xffff:
            addr = lambda ofs: word(lo + 8*ofs) + "  " if tmph < 0xffff or ofs < 2 else "----  "
        else:
            addr = lambda ofs: word(lo + 8*ofs) + "  "
        output = [[addr(ofs)] + output[val:val+8] for ofs, val in diap]
        output = [Cstr.join(" ", x) for x in output]
        # TODO: the behavior appears to be correct, now please simplify this and
        # unify with dump. Both must be clients of the same helper function.
        return list(Cstr.join("\n", output))  # Has to be a list to preserve attributes.

    @register_help("Read memory from /addr/")
    @missing_args("E: missing address")
    @morph("addr", substitute_pc, "IE: cannot have an error at this point")
    @morph("addr", to_int, "E: not a number")
    @precondition("0x0000 <= addr <= 0xffff", "E: impossible address")
    def read(self, addr):
        return mem_element(self.c.mmu, addr)

    @register_help("Write to /addr/ a /value/")
    @missing_args("E: missing argument")
    @morph("addr", substitute_pc, "IE: cannot have an error at this point")
    @morph("addr", to_int, "E: not a number")
    @morph("val", to_int, "E: not a number")
    @precondition("0x0000 <= addr <= 0xffff", "E: impossible address")
    @precondition("0x00 <= val <= 0xff", "E: impossible value")
    def write(self, addr, val):
        try:
            self.c.mmu.write(addr, val)
        except ReadOnlyError:
            return "E: cannot write to ROM"
        return ""

    @register_help("Convert hex /value/ to signed byte")
    @missing_args("E: missing argument")
    @morph("val", to_int, "E: not a number")
    @precondition("0x00 <= val <= 0xff", "E: impossible value")
    def signed(self, val):
        return str(ctypes.c_byte(val).value)

    @register_help("Show keyboard buffer")
    def showkbd(self, *a, **k):
        return "".join(chr(x) for x in self.kdb.buff)

    @register_help("Clean keyboard buffer")
    def clrkbd(self, *a, **k):
        self.kdb.buff.clear()

    @register_help("Show help for /command/")
    def help(self, command="", *a, **k):
        if not command:
            return " ".join(self.helps.keys())
        return self.helps.get(command, "E: Unknown command")

    @register_help("Reload ROM from /file/ and reset CPU")
    @missing_args("E: missing filename")
    # TODO: @ignore_extra_args  -- drop any args that are not in signature.
    @precondition("file_accessible(fname)", "E: cannot read file")
    def reload(self, fname):  # just load? the "re" part is done with "reset"
        self.reset_computer(fname)
        self.cpumonitor.reset()
        self.screen.push_chars("\n\n")
        return ""

    @register_help("Reset the computer")
    def reset(self, *a):
        self.reset_computer()
        self.cpumonitor.reset()
        self.screen.push_chars("\n\n")
        return ""

    @register_help("Update ROM from /file/ without resetting CPU state")
    @missing_args("E: missing filename")
    @precondition("file_accessible(fname)", "E: cannot read file")
    def patch(self, fname):
        # TODO: warn about patching next instruction
        # TODO: this works fine for the basic memory layout, but will break
        # once something more complex is introduced.
        with open(fname, "rb") as f:
            data = f.read()
        for addr, val in enumerate(data, BASEADDR):
            self.c.mmu.write(addr, val, False)
        return ""

    @register_help("Dump memory from /lo/ to /hi/ /as hex/ or /as ascii/")
    @missing_args("E: not enough arguments")
    @morph("lo", substitute_pc, "IE: should never result in error")
    @morph("hi", substitute_pc, "IE: should never result in error")
    @morph("lo", to_int, "E: not a number")
    @morph("hi", to_int, "E: not a number")
    @precondition("0x0000 <= lo <= 0xffff", "E: impossible loaddr")
    @precondition("0x0000 <= hi <= 0xffff", "E: impossible hiaddr")
    @precondition("lo <= hi", "E: loaddr > hiaddr")
    def dump(self, lo, hi, mod1="as", mod2="hex"):
        asascii, output = mod1 == "as" and mod2 == "ascii", []
        for i in range(lo, hi):
            if i in self.c.mmu.ioread:
                val = byte_to_repr(self.c.mmu.ioread[i].peek(), asascii)
                val = Cstr(val, curses.color_pair(100))
            else:
                val = mem_element(self.c.mmu, i, asascii)
            output.append(val)
        # Formatting the table:
        tbl_width = 8
        diap = enumerate(range(0, len(output), 8))
        addr = lambda ofs: word(lo + 8*ofs) + "  "
        output = [[addr(ofs)] + output[val:val+8] for ofs, val in diap]
        output = [Cstr.join(" ", x) for x in output]
        return list(Cstr.join("\n", output))  # Has to be a list to preserve attributes.

    @register_help("Display ASCII, dec, hex, oct and bin data about /val/")
    @missing_args("E: missing argument")
    def ascii(self, val):
        if len(val) > 0 and len(val) <= 3 and val.isdigit():
            numval, val = int(val), chr(int(val))
            if numval >= 127:
                return "E: unknown value"
        elif len(val) == 1:
            numval = ord(val)
        elif len(val) == 4 and is_hex(val[2:]):
            numval, val = int(val[2:], 16), chr(int(val[2:], 16))
        else:
            return "E: unknown value"
        return f"{val} {numval} {hex(numval)} {oct(numval)} {bin(numval)}"

    def process(self, cmd, update_last_command=True):
        # TODO: define x 42; define x 0x42.
        if not cmd[0]:  # Someone just pressed enter.
            return ""
        if cmd[0] == ";":  # Ignore comments, especially in scripts
            return ""
        if cmd[0] == "KeyboardInterrupt":
            return ""
        if cmd[0] == "!!":
            # The original plan was to have it repeat the last cmd, but this looks
            # gross and verbose. The idea is you likely know what the last cmd was.
            # You do not know it when you have executed a script, but you probably
            # don't want to re-run the entire script anyway.
            return self.process(self.lastcmd)
        torun = getattr(self, cmd[0], lambda *a, **k: f"E: Unknown command")
        if cmd[0] != "addinpt":
            args = [x for x in "".join(cmd[1:]).split(" ") if x]
        else:  # addinpt is a special case: it passes everything to keyboard verbatim.
            args = cmd[1:]

        if update_last_command:
            self.lastcmd = cmd
        try:
            return torun(*args)
        except Exception as e:
            raise Exception(str(cmd[1:]))


class CtrlConsole(Console):
    def __init__(self, cmdprocessor=None):
        self.cmdprocessor = cmdprocessor
        self.win = curses.newwin(curses.LINES - 10, 52, 10, 0)
        super(CtrlConsole, self).__init__()
        self.push_chars(">>>")
        self.win.refresh()

    def process_command(self):
        cmd = "".join(self.current_line).lstrip(">").lstrip().split(" ", 1)
        if cmd:
            self.current_line.clear()
            result = self.cmdprocessor.process(cmd)
            return result
        return ""

    def process_backspace(self):
        if len(self.current_line) <= 3:
            return
        y, x = self.win.getyx()
        self.win.addch(y, x-1, " ")
        self.current_line.pop(-1)
        self.win.move(y, x-1)
        self.win.refresh()

    def process_cc(self):  # For history processing, currently broken, at this point must be replaced with readline.
        self.cmdprocessor.history_pos = -1

    def process_key_up(self):
        for _ in range(len(self.current_line)):
            self.process_backspace()
        # TODO: this must be done on cmdproessor's side!
        self.cmdprocessor.history_pos -= 1
        if self.cmdprocessor.lastcmds:
            self.push_chars(self.cmdprocessor.lastcmds[self.cmdprocessor.history_pos])

    def process_key_down(self):
        for _ in range(len(self.current_line)):
            self.process_backspace()
        # TODO: this must be done on cmdproessor's side!
        self.cmdprocessor.history_pos += 1
        if self.cmdprocessor.lastcmds:
            self.push_chars(self.cmdprocessor.lastcmds[self.cmdprocessor.history_pos])

    def process_return(self):
        self.win.addch("\n")
        msg = self.process_command()  # process current line here
        if msg:
            self.push_chars(msg)
            self.win.addch("\n")
        self.current_line.clear()  # Now must clean again!
        self.push_chars(">>>")
        self.cmdprocessor.history_pos = -1  # resets history position


# NOTE: Vim's sign column is just 2 chars wide. To have a running
# assemly along with the code have it overlayed in the buffer?
# -- this works in neovim.
def main(stdscr):
    curses.raw()  # To pass cbreak, but this breaks everything else!
    curses.curs_set(2)
    stdscr.clear()
    curses.init_pair(100, 2, 0)  # The pair will be used to make IORead stand out
    stdscr.refresh()
    iowin = IOWin()
    stats = Stats()
    cmdprocessor = CmdProcessor(screen=iowin, cpumonitor=stats)
    console = CtrlConsole(cmdprocessor)
    currwin = console
    while True:
        key = stdscr.getkey()
        if len(key) == 1:  # normal keys
            if ord(key) == 4:  # Need special handling for Ctrl-D
                sys.exit(0)
            elif ord(key) == 3:  # Need special handling for Ctrl-C
                currwin.push_chars("\nKeyboardInterrupt\n>>>")
                currwin.current_line.clear()
            else:
                currwin.process_key(key)
        else:
            if key == "KEY_BACKSPACE":
                currwin.process_backspace()
            elif key == "KeyboardInterrupt":
                currwin.process_cc()
                currwin.pushchars("\nKeyboardInterrupt")
            elif key == "KEY_UP":
                currwin.process_key_up()
            elif key == "KEY_DOWN":
                currwin.process_key_down()
            else:
                pass  # ignore everything else
    stdscr.getkey()


if __name__ == "__main__":
    curses.wrapper(main)
