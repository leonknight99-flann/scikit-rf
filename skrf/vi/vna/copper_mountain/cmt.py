from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Sequence

import sys
from enum import Enum

import numpy as np

import skrf
from skrf.vi.validators import (
    BooleanValidator,
    EnumValidator,
    FreqValidator,
    IntValidator,
)
from skrf.vi.vna import VNA, Channel, ValuesFormat


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

    class Channel(Channel):
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


        def get_sdata(self):
            """
            Get selected trace data as an :class:`skrf.Network`

            Parameters
            ----------

            Returns
            -------
            :class:`skrf.Network`
                The measured data
            """
            return

        def get_snp_network(self, ports: Sequence | None = None) -> skrf.Network:
            """
            Get snp network as an :class:`skrf.Network`

            Parameters
            ----------
            ports: Sequence
                Which ports to get s parameters for.
            Returns
            -------
            :class:`skrf.Network`
                The measured data
            """

            if ports is None:
                ports = list(range(1, self.parent.nports + 1))

            print(ports)

            port_str = ",".join(str(port) for port in ports)

            print(port_str)

            orig_query_fmt = self.parent.query_format
            self.parent.query_format = ValuesFormat.BINARY_64

            print(self.parent.query_format)

            self.parent.active_channel = self

            nports = len(ports)

            print(f"nports: {nports}")

            ntwk = skrf.Network()
            ntwk.frequency = self.frequency
            ntwk.s = np.empty(
                shape=(len(ntwk.frequency), nports, nports), dtype=complex
            )

            print(ntwk)

            self.write('TRIG:SOUR BUS')

            self.sweep()
            raw = self.query_values(f"CALC{self.cnum}:DATA:SDAT?", container=np.array, complex_values=True)
            print(raw)
            print(raw.shape)
            self.parent.wait_for_complete()
            print(orig_query_fmt)



            self.parent.query_format = orig_query_fmt

            self.write("TRIG:SOUR INT")
            return ntwk

        def sweep(self) -> None:
            self.parent._resource.clear()
            self.write("TRIG:SING")
            print("Sweep started")
            self.parent.wait_for_complete()
            print("Sweep finished")



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
    def query_format(self) -> ValuesFormat:
        fmt = self.query("FORM:DATA?")
        if fmt == "ASC":
            self._values_fmt = ValuesFormat.ASCII
        elif fmt == "REAL32":
            self._values_fmt = ValuesFormat.BINARY_32
        elif fmt == "REAL":
            self._values_fmt = ValuesFormat.BINARY_64
        return self._values_fmt

    @query_format.setter
    def query_format(self, fmt: ValuesFormat) -> None:
        if fmt == ValuesFormat.ASCII:
            self._values_fmt = ValuesFormat.ASCII
            self.write("FORM:DATA ASC")
        elif fmt == ValuesFormat.BINARY_32:
            self._values_fmt = ValuesFormat.BINARY_32
            self.write("FORM:BORD SWAP")
            self.write("FORM:DATA REA32")
        elif fmt == ValuesFormat.BINARY_64:
            self._values_fmt = ValuesFormat.BINARY_64
            self.write("FORM:BORD SWAP")
            self.write("FORM:DATA REAL")
