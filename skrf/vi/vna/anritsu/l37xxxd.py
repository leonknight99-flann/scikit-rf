from __future__ import annotations

from enum import Enum

import numpy as np

import skrf
from skrf.vi.validators import BooleanValidator, EnumValidator, FreqValidator, IntValidator, SetValidator
from skrf.vi.vna import VNA, ValuesFormat


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
    IF1KHZ = "3"
    IF10KHZ = "4"
    IF30KHZ = "A"

class L37xxXD(VNA):
    """
    Anritsu Lightning 37xxXD VNAs.

    Lightning Models
    ================
    37369D, ...

    """

    freq_start = VNA.command(
        get_cmd='STR?',
        set_cmd='STR <arg>',
        doc="""The start frequency [Hz]""",
        validator=FreqValidator()
    )

    freq_stop = VNA.command(
        get_cmd='STP?',
        set_cmd='STP <arg>',
        doc="""The stop frequency [Hz]""",
        validator=FreqValidator()
    )

    freq_span = VNA.command(
        get_cmd='SPAN?',
        set_cmd='SPAN <arg>',
        doc="""The frequency span [Hz]""",
        validator=FreqValidator()
    )

    freq_center = VNA.command(
        get_cmd='CNTR?',
        set_cmd='CNTR <arg>',
        doc="""The center frequency [Hz]""",
        validator=FreqValidator()
    )

    npoints = VNA.command(
        get_cmd='ONP',
        set_cmd='NP <arg>',
        doc="""The number of frequency points (51, 101, 201, 401, 801, 1601)""",
        validator=SetValidator([51, 101, 201, 401, 801, 1601]) #EnumValidator(nFrequencyPoints)
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
        doc="""The number of averages (1-4095)""",
        validator=IntValidator(1, 4095, inclusive=True)
    )

    averaging_mode = VNA.command(
        get_cmd='SWAVG?',  # Returns 0 for point, 1 for sweep
        set_cmd='<arg>',
        doc="""The averaging mode (over points, over sweeps)""",
        validator=BooleanValidator('1', '0', 'SWAVG', 'PTAVG')
    )

    def __init__(self, address : str, backend : str = "@py", **kwargs):
        super().__init__(address, backend, **kwargs)

        self._resource.read_termination = "\n"
        self.model = self.id()

    @property
    def id(self):
        ''' Instrument ID string '''
        return self.query("*IDN?;")

    def clear_averaging(self):
        self.write('AON')  # Turn averaging on / refresh averaging

    @property
    def frequency(self) -> skrf.Frequency:
        f = skrf.Frequency(
            start=self.freq_start,
            stop=self.freq_stop,
            npoints=self.npoints,
            unit="hz",
        )
        return f

    @frequency.setter
    def frequency(self, f: skrf.Frequency) -> None:
        self.freq_start = f.start
        self.freq_stop = f.stop
        self.npoints = f.npoints

    @property
    def query_format(self) -> ValuesFormat:
        """
        How values are written to / queried from the instrument (ascii or
        binary)

        When transferring a large number of values from the instrument (like
        trace data), it can be done either as ascii characters or as binary.

        Transferring in binary is much faster, as large numbers can be
        represented much more succinctly.
        """
        fmt = self.query("FMX?")
        if fmt == "0":
            self._values_fmt = ValuesFormat.ASCII
        elif fmt == "2":
            self._values_fmt = ValuesFormat.BINARY_32
        elif fmt == "1":
            self._values_fmt = ValuesFormat.BINARY_64
        return self._values_fmt

    @query_format.setter
    def query_format(self, fmt: ValuesFormat) -> None:
        if fmt == ValuesFormat.ASCII:
            self._values_fmt = ValuesFormat.ASCII
            self.write("FMA")
        elif fmt == ValuesFormat.BINARY_32:
            self._values_fmt = ValuesFormat.BINARY_32
            self.write("FMC")
        elif fmt == ValuesFormat.BINARY_64:
            self._values_fmt = ValuesFormat.BINARY_64
            self.write("FMB")


    def get_sdata(self):
        """
        Get the selected trace data as an :class:`skrf.Network`

        Returns
        -------
        :class:`skrf.Network`
            The measured data
        """
        return self.get_snp_network((1,))


    def get_snp_network(self, ports: tuple | None = None) -> skrf.Network:
        """
        Get trace data as an :class:`skrf.Network`

        Parameters
        ----------
        ports: Tuple
            Which ports to get s parameters for. Can only be (1,), (2,), or (1, 2)

        Returns
        -------
        :class:`skrf.Network`
            The measured data
        """

        if ports is None:
            ports = (1,2)

        ntwk = skrf.Network()
        ntwk.frequency = self.frequency
        ntwk.s = np.empty(
            shape=(ntwk.frequency.npoints, len(ports), len(ports)), dtype=complex
        )

        self.sweep()

        if ports == (1,):
            s11 = self.query_values("OS11C;")
            print(s11)
            ntwk.s[:, 0, 0] = s11

        elif ports == (2,):
            s22 = self.query_values("OS22C;")
            print(s22)
            ntwk.s[:, 1, 1] = s22

        elif ports == (1,2) or ports == (2,1):
            s = self.query_values("OS2P;")
            print(s)
            ntwk.s[:, 0, 0] = s[:, 0]
            ntwk.s[:, 1, 1] = s[:, 1]
            ntwk.s[:, 0, 1] = s[:, 2]
            ntwk.s[:, 1, 0] = s[:, 3]

        else:
            raise ValueError("Invalid ports "+str(ports)+". Options: (1,) (2,) (1,2).")

        return ntwk

    def sweep(self, mode: SweepMode = SweepMode.NORMAL) -> None:
        """Trigger a fresh sweep."""
        self._resource.clear()
        current_sweep_mode = self.sweep_mode
        self.write('TRS')  # Trigger / restart sweep
        self.sweep_mode = current_sweep_mode
