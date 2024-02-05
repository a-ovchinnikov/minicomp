Feature: all incorrect arguments to commands result in messages to user

Background: console with basic program exists
	Given console is initiated


Scenario Outline: a user does not provide enough arguments to a command
	When a user enters "<command> <too_few_args>"
	Then they get an error
Examples:
	| command  | too_few_args |
	| ascii	   |          	  |
	| ctxt	   |          	  |
	| dump	   |          	  |
	| dump	   | 0 		  |
	| exefile  |          	  |
	| patch	   |          	  |
	| read	   |          	  |
	| reload   |          	  |
	| signed   |          	  |
	| write	   |          	  |
	| write	   | 0 		  |


Scenario Outline: a user provides incorrect arguments to a command
    Note: this is another smoketest-like group of checks. "description" field is
    **not** used in the tests and exists solely to help the reader of the spec.
    It contains current user-visible error messages, but these values are never
    checked: they can change without any warning and the only constant fact about
    them is "E:" prefix. Thus it would be counterproductive to test for messages
    contents, but the fact that a wrong command results in some error message is
    important to verify.
	When a user enters "<command> <incorrect_args>"
	Then they get an error
Examples:
	| command  | incorrect_args	  | description			|
	| ascii	   | -1        		  | E: unknown value		|
	| ascii	   | 0.6        	  | E: unknown value		|
	| ascii	   | ab 	       	  | E: unknown value		|
	| ascii	   | 127        	  | E: unknown value		|
	| ctxt	   | -1          	  | E: impossible address 	|
	| ctxt	   | 65536          	  | E: impossible address 	|
	| ctxt	   | foo          	  | E: not a number 		|
	| dump	   | s 1          	  | E: not a number 		|
	| dump	   | 1 s          	  | E: not a number 		|
	| dump	   | s s          	  | E: not a number 		|
	| dump	   | 1 0          	  | E: loaddr > hiaddr 		|
	| dump	   | -1 0          	  | E: impossible loaddr	|
	| dump	   | 0 -1          	  | E: impossibe hiaddr		|
	| dump	   | 0 65536          	  | E: impossible hiaddr	|
	| exefile  | quuxmeepfoobar324	  | E: cannot read file		|
	| step 	   | 0			  | E: cannot make less than...	|
	| step 	   | -1			  | E: cannot make less than...	|
	| step 	   | 1000001		  | E: too many steps		|
	| step 	   | foo		  | E: not a number		|
	| read 	   | foo		  | E: not a number		|
	| read 	   | -1			  | E: imposible address	|
	| read 	   | 65536		  | E: imposible address	|
	| write	   | foo 100		  | E: not a number		|
	| write	   | 100 foo		  | E: not a number		|
	| write	   | foo foo		  | E: not a number		|
	| write	   | -1 100		  | E: impossible address	|
	| write	   | 65536 100		  | E: impossible address	|
	| write	   | 100 -1		  | E: impossible value		|
	| write	   | 100 256		  | E: impossible value		|
	| signed   | foo		  | E: not a number		|
	| signed   | -1			  | E: impossible value		|
	| signed   | 256		  | E: impossible value		|
	| reload   | quuxmeepfoobar324	  | E: cannotread file		|
	| patch	   | quuxmeepfoobar324	  | E: cannotread file		|


Scenario Outline: a user provides incorrect extra arguments to a command
    Some commands can have extra arguments to augment the looks of
    output. If they are somehow incorrect then they are silently ignored.
	When a user enters "<command> <incorrect_extra_args>"
	Then they do not get an error
Examples:
	| command  | incorrect_extra_args |
	| ctxt	   | 1 foo bar         	  |
	| ctxt	   | 1 as oct         	  |
	| ctxt	   | 1 has ascii       	  |
	| dump	   | 0 10 foo bar      	  |
	| dump	   | 0 10 as oct       	  |
	| dump	   | 0 10 has ascii    	  |
