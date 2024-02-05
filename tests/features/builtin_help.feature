Feature: the console has built-in help

Background: console with basic program exists
	Given console is initiated


Scenario: a user wants to list all accessible commands
    Note, that this is **the** specification of behavior, thus it contains
    the authoritative list of commands that should be displayed by 'help'.
	When a user enters "help"
	Then they do not get an error
	And  the follwoing commands are listed
	"""
	addinpt ascii clrkbd ctxt dump exefile help patch read
	reload reset showkbd signed step write
	"""


# TODO: commands list is duplicated, however it is not immediately clear
# if it is possible to cleanly share a list of strings between several
# scenarios. This feature is unlikely to grow, so I will tolerate duplication for
# now.
Scenario Outline: a user wants to see help for a command
	When  a user enters "help <command>"
	Then they do not get an error
	And  they see help for this command
Examples:
	| command	|
	| addinpt	|
	| ascii		|
	| clrkbd	|
	| ctxt		|
	| dump		|
	| exefile	|
	| help		|
	| patch		|
	| read		|
	| reload	|
	| reset		|
	| showkbd	|
	| signed	|
	| step		|
	| write		|
