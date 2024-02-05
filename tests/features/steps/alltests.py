from copy import deepcopy
from functools import reduce
from operator import add

from behave import *


@when(u'a user enters "{command}"')
def step_impl(context, command):
    context.command = command
    context.emu_state = deepcopy(context.console.c)
    context.command_run_result = context.console.process(command.split(" ", 1))


@then(u'they do not get an error')
def step_impl(context):
    cmd_res = context.command_run_result
    failure_msg = f"Running /{context.command}/ resulted in unexpected error: {cmd_res}"
    assert cmd_res[0:2] != "E:", failure_msg


@then(u'they get an error')
def step_impl(context):
    cmd_res = context.command_run_result
    failure_msg = f"Running /{context.command}/ did not result in error, but in: {cmd_res}"
    assert cmd_res[0:2] == "E:", failure_msg


@then(u'the follwoing commands are listed')
def step_impl(context):
    expected_cmds = context.text.split()
    actual_cmds = context.command_run_result.split()

    failure_msg = f"Output mismatch\nExpected to see: {expected_cmds}\nGot: {actual_cmds}"
    assert set(actual_cmds) == set(expected_cmds), failure_msg
    assert len(actual_cmds) == len(expected_cmds), failure_msg


# TODO: ------------- stepping.py
@then(u'a single instruction is executed')
def step_impl(context):
    context.execute_steps(u'''
            then "1" instructions are executed
            ''')


@then(u'no instructions are executed')
def step_impl(context):
    context.execute_steps(u'''
            then "0" instructions are executed
            ''')


@then(u'"{k}" instructions are executed')
def step_impl(context, k):
    # Checking for just PC won't work. A better indicator of step working is
    # having several accesses to memory, at least one, but no more than four.
    # This would decouple the test from underlying test binary and would work
    # with effectively any non-degenrative binary.

    k = int(k)  # TODO: parse_int
    read_calls = context.console.c.mmu.read.mock_calls
    # At least one byte has to be read per instruction:
    assert len(read_calls) >= k, (f"Expected at least {k} memory reads, "
                                  f"got {len(read_calls)}")
    # The maximal number of memory reads per instruction is 4:
    #   read one byte of an instruction, realize it is an indirect LDA
    #   read two bytes of address at which to look for a value (2 bytes ≡ 2 reads)
    #   read one byte of value from an address above.
    # This pattern could happen multiple times in a row, so the maximum total
    # number of reads is equal to 4x number of steps.
    assert len(read_calls) <= 4*k, (f"Expected at most {4*k} memory reads, "
                                    f"got {len(read_calls)}")

# TODO: --- helper_functions.py
@then(u'they receive "{resval}" value of k')
def step_impl(context, resval):
    msg = (f"Unexpected result of running /{context.command}/:\n"
           f"Excpected - {resval}\n"
           f"Received  - {context.command_run_result}"
    )
    assert context.command_run_result == resval, msg


@then(u'they see "{_ascii}", "{_dec}", "{_hex}", "{_oct}" and "{_bin}" representation of it')
def step_impl(context, _ascii, _dec, _hex, _oct, _bin):
    r_ascii, r_dec, r_hex, r_oct, r_bin = context.command_run_result.split()
    assert r_ascii == _ascii, f"ASCII value mismatch: expected {_ascii}, got {r_ascii}"
    assert r_dec == _dec, f"decimal value mismatch: expected {_dec}, got {r_dec}"
    assert r_hex[2:] == _hex, f"hexadecimal value mismatch: expected {_hex}, got {r_hex}"
    assert r_oct[2:] == _oct, f"octal value mismatch: expected {_oct}, got {r_oct}"
    assert r_bin[2:] == _bin, f"binary value mismatch: expected {_bin}, got {r_bin}"


# TODO: --- cpu_interactions.py
@when(u'a user does some interaction with the emulator')
def step_impl(context):
    # Some interacions with the computer, should be randomized?
    # Or maybe this should be a set of examples to run different queries.
    # This better be a strategy for creating possible interactions.
    context.execute_steps(u'''
            when a user enters "step 10"
            ''')


@then(u'CPU is in initial state')
def step_impl(context):
    msg = f"Expected to see PC on the start position, but got {context.console.c.r.pc}"
    assert context.console.c.r.pc == 0xe000, msg
    msg = f"Expected empty A, but got {context.console.c.r.a}"
    assert context.console.c.r.a == 0x00, msg
    msg = f"Expected empty X, but got {context.console.c.r.x}"
    assert context.console.c.r.x == 0x00, msg
    # Would be nice to express this concept in a one-liner:
    # expect(empty(foo))
    msg = f"Expected empty Y, but got {context.console.c.r.y}"
    assert context.console.c.r.y == 0x00, msg
    msg = f"Expected SP to point to the top of stack, but got {context.console.c.r.s}"
    assert context.console.c.r.s == 0xff, msg


def mem_blocks(readonly, device):
    return [b for b in device.mmu.blocks if b["readonly"] == readonly]


def rom_blocks(device):
    return mem_blocks(True, device)


def ram_blocks(device):
    return mem_blocks(False, device)


def has_identical_counterpart(block, other_blocks):
    # There will be less than ten blocks to check in 99.999% of cases, this is fine.
    for pot_ctrpart in other_blocks:
        if block == pot_ctrpart:
            return True, None
    return False, block


def find_mismatching_blocks(old_rom_blocks, new_rom_blocks):
    blocks_paired = [has_identical_counterpart(b, old_rom_blocks) for b in new_rom_blocks]
    return list(filter(lambda b: not b[0], blocks_paired))


@then(u'ROM is unchanged')
def step_impl(context):

    old_rom_blocks = rom_blocks(context.emu_state)
    new_rom_blocks = rom_blocks(context.console.c)
    msg = (f"ROM blocks number mismatch after running /{context.command}/:\n"
           f"{len(old_rom_blocks)=}\n"
           f"{len(new_rom_blocks)=}"
    )
    assert len(old_rom_blocks) == len(new_rom_blocks), msg

    mismatching_blocks = find_mismatching_blocks(old_rom_blocks, new_rom_blocks)
    all_blocks_match = not mismatching_blocks
    msg = f"Some ROM blocks changed: {', '.join(b['start'] for b in mismatching_blocks)}"
    assert all_blocks_match, msg


@then(u'RAM is cleared')
def step_impl(context):
    new_ram_blocks = ram_blocks(context.console.c)
    non_empty_blocks = [b for b in new_ram_blocks if any(b["memory"])]
    all_blocks_are_empty = not non_empty_blocks
    msg = (f"These memory blocks are not empty: "
           f"{', '.join(b['start'] for b in non_empty_blocks)}")

    assert all_blocks_are_empty, msg


@then(u'ROM is new')
def step_impl(context):
    old_rom_blocks = rom_blocks(context.emu_state)
    new_rom_blocks = rom_blocks(context.console.c)
    mismatching_blocks = find_mismatching_blocks(old_rom_blocks, new_rom_blocks)
    rom_changed = len(mismatching_blocks) >= 1
    assert rom_changed, "ROM was supposed to change, but it did not"


@then(u'CPU state is old')
def step_impl(context):
    msg = f"Expected to see PC on the same position, but it was changed"
    assert context.console.c.r.pc == context.emu_state.r.pc, msg
    msg = f"Expected identical As between operation, but it was changed"
    assert context.console.c.r.a == context.emu_state.r.a, msg
    msg = f"Expected identical Xs, but it was changed"
    assert context.console.c.r.x == context.emu_state.r.x, msg
    msg = f"Expected identical Ys, but it was changed"
    assert context.console.c.r.y == context.emu_state.r.y, msg
    msg = f"Expected identical SPs, but it was changed"
    assert context.console.c.r.s == context.emu_state.r.s, msg


@then(u'RAM is unchanged')
def step_impl(context):
    old_ram_blocks = ram_blocks(context.emu_state)
    new_ram_blocks = ram_blocks(context.console.c)
    mismatching_blocks = find_mismatching_blocks(old_ram_blocks, new_ram_blocks)
    all_ram_blocks_match = not mismatching_blocks
    msg = f"Some RAM blocks changed: {', '.join(b['start'] for b in mismatching_blocks)}"
    assert all_ram_blocks_match, msg


# TODO: --- memory_interactions.py
def no_error(result):
    return result[0:2] != "E:"


@then(u'value at this address is returned to the user')
def step_impl(context):
    result = context.command_run_result
    msg = f"Expected no errors when running /{context.command}/, but got {result}"
    assert no_error(context.command_run_result), msg
    msg = f"Unexpected result when running /{context.command}/: {result}"
    assert len(context.command_run_result) == 2, msg


@then(u'value at {address} is set to {val}')
def step_impl(context, address, val):
    msg = "Read after write mismatch"
    assert context.console.c.mmu.read(int(address, 16)) == int(val, 16), msg


def not_empty(iterable):
    if isinstance(iterable, str):
        return len(iterable.translate(str.maketrans({' ': '', '\n': ''}))) > 0
    elif isinstance(iterable, list):
        return len(iterable) > 0
    else:
        return False


@then(u'a table view of {lo}:{hi} region of memory is returned')
def step_impl(context, lo, hi):
    # TODO: split this one. It also does not fully check the layout now.
    lo = int(lo, 16)
    hi = int(hi, 16)
    output = context.command_run_result
    output = [[x for x in y if not_empty(x)] for y in output if not_empty(y)]
    expected_total = hi - lo
    # There are len(output) addresses in the resulting string.
    actual_num_of_bytes = sum(len(x) for x in output) - len(output)
    msg = (f"Expected {expected_total} bytes, but got {actual_num_of_bytes}")
    assert expected_total == actual_num_of_bytes, msg
    returned_lo = int(output[0][0].rstrip(), 16)
    assert returned_lo == lo, f"Lo addr mismatch: asked for {lo}, got {returned_lo}"

    returned_hi = int(output[-1][0].rstrip(), 16)
    # NOTE: width is fixed for now and for all foreseeable future due to the nature of
    # the tool. DO NOT try and generalize this.
    expected_display_hi = (hi / 8 - 1) * 8
    msg = f"Displayed hi addr mismatch: expected {expected_display_hi}, got {returned_hi}"
    assert returned_hi == expected_display_hi, msg
    # Not very useful, but still checks that I am not too far off:
    errors = []
    for row in output:
        addr, *vals = row
        addr = int(addr, 16)
        for offset, val in enumerate(vals):
            if "N" not in val:
                if " " not in val:
                    val = int(val, 16)
                else:
                    val = chr(val)
                expected = context.console.c.mmu.read(addr + offset)
                if val != expected:
                    errors.append(addr + offset)
    no_errors = len(errors) == 0
    msg = (f"Got mismatches in these positions: {errors[:4]}"
            f"{' and {k} others'.format(k=len(errors)-4) if len(errors) > 4 else ''}")
    assert no_errors, msg

@then(u'a table view surrounding address is returned')
def step_impl(context):
    # TODO: implement this
    pass

@then(u'the table view contains three memory lines')
def step_impl(context):
    assert len([x for x in context.command_run_result if x != '\n']) == 3, f"Unexpected number of lines {context.command_run_result}"

@then(u'the first element of middle line is the value at {address}')
def step_impl(context, address):
    # TODO: implement this
    pass

def filter_newlines(lst):
    # TODO: dump returns newlines packed as lists. Fix that or elaborate why.
    return [x for x in lst if x !='\n' and x !=['\n']]

@then(u'the {number} line contains eight or less values')
def step_impl(context, number):
    # TODO: have a type to convert number from string representation to position in a list
    if number == "first":
        number = 0
    elif number == "middle":
        number = 2
    elif number == "last":
        number = 2
    else:
        raise Exception(f"This was not supposed to happen, but got {number=}")
    output = filter_newlines(context.command_run_result)
    line = [x for x in output[number] if not_empty(x)]
    addr, *vals = line
    assert len(vals) == 8, f"Expected 8 elements per line, but got {len(vals)}"
    def filter_outranges(lst):
        return [x for x in vals if not x.isalnum()]
    assert len(filter_outranges(vals)) <= 8, f"Got unexpected number of out of range values: {len(filter_outranges(vals))}"


@then(u'values outside of address range are represented as {outrange_repr}')
def step_impl(context, outrange_repr):
    def outliers_represented_as(rpr, addr, val):
        if addr > 0xffff or addr < 0:
            return val == rpr
        return True
    output = filter_newlines(context.command_run_result)
    target_address = int(output[1][0].rstrip(), 16)
    shown_bytes = reduce(add, [list(filter(not_empty, x))[1:] for x in output])
    byte_addr = list(enumerate(shown_bytes, target_address - 8))
    msg = f"Some outliers were not represented correctly"
    assert all(outliers_represented_as(outrange_repr, addr, val) for addr, val in byte_addr), msg


@then(u'unmaped values within address range are represented as {unmapped_repr}')
def step_impl(context, unmapped_repr):
    # A kilobyte right before e000 is intentionally unmapped
    # TODO: this stuff below is badly duplicated
    def filter_outranges(lst):
        return [x for x in lst if 0 <= x[0] and x[0] <= 0xffff]
    def unmapped_are_represented_as(rpr, addr, val):
        try:
            context.console.c.mmu.getBlock(addr)
        except IndexError:
            return val == rpr
        return True
    output = filter_newlines(context.command_run_result)
    target_address = int(output[1][0].rstrip(), 16)
    shown_bytes = reduce(add, [list(filter(not_empty, x))[1:] for x in output])
    byte_addr = list(filter_outranges(enumerate(shown_bytes, target_address - 8)))
    assert all(unmapped_are_represented_as(unmapped_repr, addr, val) for addr, val in byte_addr), msg


@then(u'addresses outside the range are represented as {outaddr_repr}')
def step_impl(context, outaddr_repr):
    output = filter_newlines(context.command_run_result)
    for idx, line in enumerate(output):
        if not line[0].strip().isalnum():
            if idx == 0 or idx == 2:
                msg = (f"{'First' if idx == 0 else 'Last'} line does not start with "
                        f"{outaddr_repr}, but with {line[0]}")
                assert line[0].startswith(outaddr_repr), msg
            else:
                raise Exception(f"Middle line address is broken: {line[0]}")
