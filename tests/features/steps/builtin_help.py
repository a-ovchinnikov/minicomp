from behave import *


@then(u'they see help for this command')
def step_impl(context):
    # There is no good way to test that help message is correct,
    # however it should not be empty.
    result = context.command_run_result
    msg = f"Expected to get something when running /{context.command}/, but got nothing"
    assert context.command_run_result, msg
    msg = f"Unexpected error when running /{context.command}/: {result}"
    assert context.command_run_result[0:2] != "E:", msg
