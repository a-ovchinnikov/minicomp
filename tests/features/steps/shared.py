import unittest.mock as mock

from behave import *

from minicomp import main


class PhonyScreen(main.Console):
    def __init__(self):
        self.current_line = []
        self.chars = []

    def process_char(self, char):
        self.push_char(char)

    def push_chars(self, chars):
        for ch in chars:
            for subch in ch:
                self.push_char(subch)

    def push_char(self, char):
        self.chars.append(char)

    def write(self, *a, **k):
        pass

    def activate(self):
        pass

    def deactivate(self):
        pass


class PhonyStats:
    def __init__(self):
        pass

    def reset(self):
        pass

    def update_stats(self, cpu, refresh=False):
        pass


@given("console is initiated")
def step_impl(context):
    # MagicMocking these messes with decorators and results in extra values with help
    console = main.CmdProcessor(screen=PhonyScreen(), cpumonitor=PhonyStats())
    # To proxy calls to mmu and have easy access to all calls and args:
    console.c.mmu = mock.Mock(wraps=console.c.mmu,
            ioread=console.c.mmu.ioread,
            iowrite=console.c.mmu.iowrite,
            blocks=console.c.mmu.blocks)
    context.console = console
