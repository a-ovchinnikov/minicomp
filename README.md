# Minicomp

A larva of a tool for visual assessing and manual testing of 6502 code written
for systems with tiny terminals. Its primary goal is to answer the question
"How usable a system with 20x4 symbols display could be made and if 20x4 is
unusable then what about 50x8?" without soldering a 6502 computer together.

The system as it is now is a bit of a stream of consiousness written down
during some sparse odd free hours. Its emulation core is derived from
[py65emu](https://github.com/docmarionum1/py65emu).  It needs some 6502
assembly, I tested it with [xa](https://github.com/docmarionum1/py65emu).
Features most important for me are specified with
[Gherkin](https://cucumber.io/docs/gherkin/) and could be tested with
[behave](https://behave.readthedocs.io/en/latest/) by running ```./bhave``` in
the root of the package. ```./dtest``` runs all doctests. ```./go``` starts
the emulator.
 
I planned to run _minicomp_ inside Vim in a window alongside code I develop, a
quick and dirty set-up for doing so could be found in *vimrc_sample_setup*. I
tested it with Vim 8.1.x, any version that supports terminal mode should work.

Many planned features are still missing, some code pieces which must be
separate are still fused together for historical and economic reasons, bugs are
likely lurking somewhere.
