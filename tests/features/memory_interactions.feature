Feature: memory contents of the emulated computer could be manipulated from the console

Background: console with a basic program exists
	Given console is initiated


Scenario Outline: a user wants to read value from a specific address
	When a user enters "read <valid_RAOM_address>"
	Then value at this address is returned to the user
Examples:
	 | valid_RAOM_address	| Comments					|
	 | 0xe000		| Default PC, always has some contents		|
	 | 0x0001		| Zero page, always present			|


Scenario Outline: a user wants to modify a RAM cell
	When a user enters "write <valid_RAM_address> <val>"
	Then value at <valid_RAM_address> is set to <val>
Examples:
	| valid_RAM_address	| val	| Comments				|
	| 0x500			| 0x42	|Some existing address in RAM 		|
	| 0x0001		| 0x42	|Zero page, always present		|


Scenario: a user wants to modify a ROM cell
	When a user enters "write 0xe000 0x42"
	Then they get an error


Scenario Outline: a user wants to see contents of a memory region
    Memory cells which are not present should be displayed as "NA"
	When a user enters "dump <lo> <hi>"
	Then a table view of <lo>:<hi> region of memory is returned
Examples:
	| lo		| hi		| Comments				|
	| 0x0000	| 0x0010	| Empty space on zero page		|


Scenario Outline: a user wants to see surrounding context of an address
	When a user enters "ctxt <address>"
	Then a table view surrounding address is returned
	And  the table view contains three memory lines
	And  the first element of middle line is the value at "<address>"
	And  the first line contains eight or less values
	And  the middle line contains eight or less values
	And  the last line contains eight or less values
	And  values outside of address range are represented as --
	And  unmaped values within address range are represented as NA
	And  addresses outside the range are represented as ----
Examples:
	| address	| Comments						|
	| 0x0000	| Entire first line is outside the range		|
	| 0x0001	| Part of the first line is outside the range		|
	| pc		| PC could be used as alias, also has unmapped area	|
	| 0xffff	| Third line is off-range, parts of second too 		|
