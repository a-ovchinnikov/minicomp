Feature: helper functions exist to help user with their debugging tasks


Background: console with basic program exists
	Given console is initiated


Scenario Outline: a user wants to check ASCII value of a byte
	When a user enters "ascii <symbol>"
	Then they see "<ASCII>", "<decimal>", "<hexadecimal>", "<octal>" and "<binary>" representation of it
Examples:
	| symbol | ASCII| decimal| hexadecimal  | octal	| binary	|
	| a	 | a	| 97	 | 61		| 141	| 1100001	|
	| 97	 | a	| 97	 | 61		| 141	| 1100001	|
	| 0x61	 | a	| 97	 | 61		| 141	| 1100001	|


Scenario Outline: a user wants to convert a byte to signed offset
	When a user enters "signed <k>"
	Then they receive "<signed_offset>" value of k
Examples:
	| k	| signed_offset |
	| 0xbf	| -65		|
	| 0x0f	| 15		|
	| 250	| -6		|
	| 127	| 127		|
	| 128	| -128		|
	| 0x7f	| 127		|
	| 0x80	| -128		|
