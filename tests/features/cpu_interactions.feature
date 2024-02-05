Feature: emulator state could be altered from console

Background: console with basic program exists
	Given console is initiated


Scenario: a user wants to reset the cpu
	When a user does some interaction with the emulator
	And  a user enters "reset"
	Then CPU is in initial state
	And  ROM is unchanged
	And  RAM is cleared


Scenario: a user can patch ROM from file without resetting emulator state
	When a user does some interaction with the emulator
	And  a user enters "patch empty.bin"
	Then ROM is new
	And  CPU state is old
	And RAM is unchanged


Scenario: a user can reinitialize the emulator with a different binary
	When a user does some interaction with the emulator
	And  a user enters "reload empty.bin"
	Then ROM is new
	And CPU is in initial state
	And RAM is cleared
