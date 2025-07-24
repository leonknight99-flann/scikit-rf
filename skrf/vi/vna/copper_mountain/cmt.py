from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Sequence

import sys
from enum import Enum

import skrf
from skrf.vi import vna
from skrf.vi.validators import (
    BooleanValidator,
    EnumValidator,
    FreqValidator,
    IntValidator,
)
from skrf.vi.vna import VNA


class SweepType(Enum):
    LINEAR = "LIN"
    LOG = "LOG"
    SEGMENT = "SEGM"
    POWER = "POW"
    # CW = "CW"
    # PHASE = "PHAS"

class SweepMode(Enum):
    HOLD = "HOLD"
    CONTINUOUS = "CONT"
    GROUPS = "GRO"
    SINGLE = "SING"


class CMT(VNA):
    """
    Copper Mountain S2 & S4 VNAs.

    S2 Models
    =========
    S5045, S5065, S5085, S5180, S5180B, S5243, S7530, S5048
    M5045, M5065, M5090, M5180
    SC5065, SC5090, SC7540
    C1209, C1220, C2209, C2220, C4209, C4220
    Full-Size 304/1, Full-Size 804/1, Full-Size 814/1

    S4 Models
    =========
    C1409, C1420, C2409, C2420, C4409, C4420
    Full-Size 808/1

    """

    _models = {
        "default": {"nports": 2, "unsupported": []},
        "C4220": {"nports": 2, "unsupported": []},
    }

    class Channel(vna.Channel):
        def __init__(self, parent, cnum: int, cname: str):
            super().__init__(parent, cnum, cname)

        freq_start = VNA.command(
            get_cmd="SENS<self:cnum>:FREQ:STAR?",
            set_cmd="SENS<self:cnum>:FREQ:STAR <arg>",
            doc="""The start frequency [Hz]""",
            validator=FreqValidator(),
        )

        freq_stop = VNA.command(
            get_cmd="SENS<self:cnum>:FREQ:STOP?",
            set_cmd="SENS<self:cnum>:FREQ:STOP <arg>",
            doc="""The stop frequency [Hz]""",
            validator=FreqValidator(),
        )

        freq_span = VNA.command(
            get_cmd="SENS<self:cnum>:FREQ:SPAN?",
            set_cmd="SENS<self:cnum>:FREQ:SPAN <arg>",
            doc="""The frequency span [Hz].""",
            validator=FreqValidator(),
        )

        freq_center = VNA.command(
            get_cmd="SENS<self:cnum>:FREQ:CENT?",
            set_cmd="SENS<self:cnum>:FREQ:CENT <arg>",
            doc="""The frequency center [Hz].""",
            validator=FreqValidator(),
        )

        npoints = VNA.command(
            get_cmd="SENS<self:cnum>:SWE:POIN?",
            set_cmd="SENS<self:cnum>:SWE:POIN <arg>",
            doc="""The number of frequency points. Sets the frequency step as a
                side effect
            """,
            validator=IntValidator(),
        )

        if_bandwidth = VNA.command(
            get_cmd="SENS<self:cnum>:BWID?",
            set_cmd="SENS<self:cnum>:BWID <arg>",
            doc="""The IF bandwidth [Hz]""",
            validator=FreqValidator(),
        )

        sweep_type = VNA.command(
            get_cmd="SENS<self:cnum>:SWE:TYPE?",
            set_cmd="SENS<self:cnum>:SWE:TYPE <arg>",
            doc="""The type of sweep (linear, log, segment, power)""",
            validator=EnumValidator(SweepType),
        )

        is_continuous = VNA.command(
            get_cmd="INIT:CONT?",
            set_cmd="INIT:CONT <arg>",
            doc="""Turns the continuous sweep mode on or off""",
            validator=BooleanValidator()
        )

        # No measurement_numbers

        averaging_on = VNA.command(
            # Note only one type of averaging is supported
            get_cmd="SENS<self:cnum>:AVER:STAT?",
            set_cmd="SENS<self:cnum>:AVER:STAT <arg>",
            doc="""Whether averaging is on or off""",
            validator=BooleanValidator(),
        )

        averaging_count = VNA.command(
            get_cmd="SENS<self:cnum>:AVER:COUN?",
            set_cmd="SENS<self:cnum>:AVER:COUN <arg>",
            doc="""The number of measurements combined for an average""",
            validator=IntValidator(1, 999),
        )

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

        def get_snp_network(self, ports: Sequence | None = None, data_level: str = 'calibrated') -> skrf.Network:
            """
            Get trace data as an :class:`skrf.Network`

            Parameters
            ----------
            ports: Sequence
                Which ports to get s parameters for. Can only be 1, 2, or (1, 2)
            data_level: str
                Where in the data processing should the s-parameters be taken from.
                Options are 'raw', 'corrected', 'formated'. Corrected is the data
                after calibration, and formatted is the data after all processing
                (like smoothing, etc).
                (Default to calibrated)

            Returns
            -------
            :class:`skrf.Network`
                The measured data
            """
            if data_level not in ('raw', 'corrected', 'formatted'):
                raise ValueError("data_level must be one of 'raw', 'corrected', or 'formatted'")

            if ports is None:
                ports = (1,2)
            return


    def __init__(self, address: str, backend: str = "@py", **kwargs) -> None:
        super().__init__(address, backend, **kwargs)

        self._resource.read_termination = "\n"

        self.create_channel(1, "Channel 1")
        self.active_channel = self.ch1

        self.model = self.id.split(",")[1]
        if self.model not in self._models:
            print(
                f"WARNING: This model ({self.model}) has not been tested with "
                "scikit-rf. By default, all features are turned on but older "
                "instruments might be missing SCPI support for some commands "
                "which will cause errors. Consider submitting an issue on GitHub to "
                "help testing and adding support.",
                file=sys.stderr,
            )


    def _supports(self, feature: str) -> bool:
        model_config = self._models.get(self.model, self._models["default"])
        return feature not in model_config["unsupported"]

    def _model_param(self, param: str):
        model_config = self._models.get(self.model, self._models["default"])
        return model_config[param]

    @property
    def nports(self) -> int:
        if self._supports("nports"):
            return int(self.query("SERV:PORT:COUN?"))
        else:
            return self._model_param("nports")

    @property
    def active_channel(self) -> Channel | None:
        num = int(self.query("SERV:CHAN:ACT?"))
        return getattr(self, f"ch{num}", None)

    @active_channel.setter
    def active_channel(self, ch: Channel) -> None:
        if self.active_channel.cnum == ch.cnum:
            return
        self.write(f"DISP:WIND{ch.cnum}:ACT")

    @property
    def query_format(self) -> vna.ValuesFormat:
        fmt = self.query("FORM:DATA?")
        if fmt == "ASC":
            self._values_fmt = vna.ValuesFormat.ASCII
        elif fmt == "REAL32":
            self._values_fmt = vna.ValuesFormat.BINARY_32
        elif fmt == "REAL":
            self._values_fmt = vna.ValuesFormat.BINARY_64
        return self._values_fmt

    @query_format.setter
    def query_format(self, fmt: vna.ValuesFormat) -> None:
        if fmt == vna.ValuesFormat.ASCII:
            self._values_fmt = vna.ValuesFormat.ASCII
            self.write("FORM:DATA ASC")
        elif fmt == vna.ValuesFormat.BINARY_32:
            self._values_fmt = vna.ValuesFormat.BINARY_32
            self.write("FORM:BORD SWAP")
            self.write("FORM REA32")
        elif fmt == vna.ValuesFormat.BINARY_64:
            self._values_fmt = vna.ValuesFormat.BINARY_64
            self.write("FORM:BORD SWAP")
            self.write("FORM REAL")
