Feature: a user can step through code

Background: console with a basic program exists
	Given console is initiated


Scenario: a user does not supply the number of steps to step through
	When a user enters "step"
	Then  a single instruction is executed


Scenario Outline: a user supplied the number of steps to step through
	When a user enters "step <k>"
	Then  "<k>" instructions are executed
Examples:
	| k	|
	| 10	|
	| 100	|


Scenario Outline: a user requests too few steps
	When a user enters "step <k>"
	Then  no instructions are executed
Examples:
	| k	|
	| 0	|
	| -1	|


Scenario: a user requests too many steps
	When a user enters "step 1000001"
	Then  no instructions are executed
