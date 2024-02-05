import array
from collections import namedtuple


class MemoryRangeError(ValueError):
    pass


class ReadOnlyError(TypeError):
    pass


def RAM(lower, upper):
    """Helper function to make Memory creation easier"""
    return (lower, upper)

# TODO: start_addr, end_addr, @morph(..., to_addr)
def ROM(lower, upper, f):
    """Helper function to make Memory creation easier"""
    return (lower, upper, True, f)


class MemIODevice:
    """Base class for all memory IO devices"""
    def __init__(self):
        pass

    def write(self, value):
        pass

    def read(self, value):
        pass

    def peek(self):
        pass


class Screen(MemIODevice):
    def write(self, value):
        with open("/tmp/screenio.log", "a") as f:
            f.write(f"Screen got {chr(value)}\n")


class Keyboard(MemIODevice):
    def __init__(self, buff=""):
        self.initial = buff[:]
        self.reset()

    def read(self):
        if not self.buff:
            return 0
        retval = self.buff.pop(0)
        return retval

    def extend(self, values):
        self.buff.extend(ord(x) for x in values)

    def peek(self):
        return self.buff[0] if self.buff else 0

    def reset(self):
        self.buff = [ord(x) for x in self.initial]


class MMU:
    def __init__(self, *blocks):
        """
        Initialize the MMU with the blocks specified in blocks.  blocks
        is a list of 5-tuples, (start, length, readonly, value, valueOffset).

        See `addBlock` for details about the parameters.
        """

        # Different blocks of memory stored seperately so that they can
        # have different properties.  Stored as dict of "start", "length",
        # "readonly" and "memory"
        self.blocks = []
        self.iowrite = {}
        self.ioread = {}

        for b in blocks:
            self.addBlock(*b)

    def register_io(self, address, iodevice, direction="w"):
        # TODO: check that a device is not added twice
        # iodevice is a method that accepts single value
        # one generic write method is not enough: consider devices that
        # require a data bus and a control bus on two separate addresses
        # this would require setting one and then another.
        if direction == "w":
            self.iowrite[address] = iodevice
        elif direction == "r":
            self.ioread[address] = iodevice
        else:
            print("Error: cannot register {iodevice}, expected direction in (r, w), got {direction}")

    def reset(self):
        """
        In all writeable blocks reset all values to zero.
        """
        for b in self.blocks:
            if not b['readonly']:
                b['memory'] = array.array('B', [0]*b['length'])

    def addBlock(self, start, length, readonly=False, value=None, valueOffset=0):
        """
        Add a block of memory to the list of blocks with the given start address
        and length; whether it is readonly or not; and the starting value as either
        a file pointer, binary value or list of unsigned integers.  If the
        block overlaps with an existing block an exception will be thrown.

        Parameters
        ----------
        start : int
            The starting address of the block of memory
        length : int
            The length of the block in bytes
        readOnly: bool
            Whether the block should be read only (such as ROM) (default False)
        value : file pointer, binary or lint of unsigned integers
            The intial value for the block of memory. Used for loading program
            data. (Default None)
        valueOffset : integer
            Used when copying the above `value` into the block to offset the
            location it is copied into. For example, to copy byte 0 in `value`
            into location 1000 in the block, set valueOffest=1000. (Default 0)
        """

        # check if the block overlaps with another
        for b in self.blocks:
            if ((start+length > b['start'] and start+length < b['start']+b['length']) or
                    (b['start']+b['length'] > start and b['start']+b['length'] < start+length)):
                raise MemoryRangeError()

        newBlock = {
            'start': start, 'length': length, 'readonly': readonly,
            'memory': array.array('B', [0]*length)
        }

        # TODO: implement initialization value
        if type(value) == list:
            for i in range(len(value)):
                newBlock['memory'][i+valueOffset] = value[i]

        elif value is not None:
            a = array.array('B')
            a.frombytes(value.read())
            for i in range(len(a)):
                newBlock['memory'][i+valueOffset] = a[i]

        self.blocks.append(newBlock)

    def getBlock(self, addr):
        """
        Get the block associated with the given address.
        """

        for b in self.blocks:
            if addr >= b['start'] and addr < b['start']+b['length']:
                return b

        raise IndexError(f"Address {hex(addr)}({addr}) not found in any blocks!")

    def getIndex(self, block, addr):
        """
        Get the index, relative to the block, of the address in the block.
        """
        return addr-block['start']

    def write(self, addr, value, protect_rom=True):
        """
        Write a value to the given address if it is writeable.
        """
        if addr in self.iowrite:
            self.iowrite[addr](value)
        else:
            b = self.getBlock(addr)
            if b['readonly'] and protect_rom:
                raise ReadOnlyError()
            i = self.getIndex(b, addr)
            b['memory'][i] = value & 0xff

    def read(self, addr):
        """
        Return the value at the address.
        """
        if addr in self.ioread:
            return self.ioread[addr].read()
        else:
            b = self.getBlock(addr)
            i = self.getIndex(b, addr)
            return b['memory'][i]

    def readWord(self, addr):
        return (self.read(addr+1) << 8) + self.read(addr)
