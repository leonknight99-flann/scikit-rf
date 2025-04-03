from enum import Enum

from skrf.vi.validators import (
    BooleanValidator,
    EnumValidator,
)
from skrf.vi.vna import VNA


class nFrequencyPoints(Enum):
    # Check if this is correct as it may need to take note of how each is
    # returned when ONP is called - same for the below
    NP51 = "51"
    NP101 = "101"
    NP201 = "201"
    NP401 = "401"
    NP801 = "801"
    NP1601 = "1601"

class PlotType(Enum):
    LOGMAG = "MAG"
    PHASE = "PHA"
    LINEAR = "LIN"
    LINPHASE = "LPH"
    LOGPHASE = "MPA"

class SweepMode(Enum):
    HOLD = "HLD"  # Hold at current point
    SINGLE = "SING"  # Single sweep
    NORMAL = "SWP"  # Normal sweep
    CONTINUE = "CTN"  # Continue sweep from current point

class IFbwMode(Enum):
    IF10HZ = "1"
    IF100HZ = "2"
    IF1KHZ = "N"
    IF10KHZ = "4"
    IF30KHZ = "A"

class L37xxXD(VNA):
    """
    Class for Anritsu Lightning 37xxXD VNAs.

    """

    def __init__(self, address : str, backend : str = "@py", **kwargs):
        super().__init__(address, backend, **kwargs)

        self._resource.read_termination = "\n"

    freq_start = VNA.command(
        get_cmd='STR?',
        set_cmd='STR <arg>',
        doc="""The start frequency [Hz]"""
    )

    freq_stop = VNA.command(
        get_cmd='STP?',
        set_cmd='STP <arg>',
        doc="""The stop frequency [Hz]"""
    )

    freq_span = VNA.command(
        get_cmd='SPAN?',
        set_cmd='SPAN <arg>',
        doc="""The frequency span [Hz]"""
    )

    freq_center = VNA.command(
        get_cmd='CNTR?',
        set_cmd='CNTR <arg>',
        doc="""The center frequency [Hz]"""
    )

    npoints = VNA.command(
        get_cmd='ONP',
        set_cmd='NP <arg>',
        doc="""The number of frequency points (51, 101, 201, 401, 801, 1601)""",
        validator=EnumValidator(nFrequencyPoints)
    )

    if_bandwidth = VNA.command(
        get_cmd='IFX?',
        set_cmd='IF<arg>',
        doc="""The IF bandwidth (10Hz, 100Hz, 1kHz, 10kHz, 30kHz)""",
        validator=EnumValidator(IFbwMode)
    )

    sweep_mode = VNA.command(
        get_cmd='SWP?',
        set_cmd='<arg>',
        doc="""The sweep mode (HOLD, SINGLE, NORMAL, CONTINUE)""",
        validator=EnumValidator(SweepMode)
    )

    averaging_on = VNA.command(
        get_cmd='AOF?',
        set_cmd='AO<arg>',
        doc="""Averaging on/off""",
        validator=BooleanValidator('1', '0', 'N','F',)
    )

    averaging_count = VNA.command(
        get_cmd='AVG?',
        set_cmd='AVG <arg>',
    )

    def reset_averaging(self):
        self.write('AON')
