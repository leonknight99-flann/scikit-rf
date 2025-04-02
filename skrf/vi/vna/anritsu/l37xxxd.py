from skrf.vi.vna import VNA


class L37xxXD(VNA):
    """
    Class for Anritsu Lightning 37xxXD VNAs.

    Parameters
    ----------
    address : str
        VISA address of the VNA.
    **kwargs : keyword arguments
        Additional keyword arguments to be passed to the parent class.

    Attributes
    ----------
    frequency : numpy.ndarray
        Frequency array in Hz.
    nports : int
        Number of ports of the VNA.
    npoints : int
        Number of frequency points.
    """

    def __init__(self, address, **kwargs):
        super().__init__(address, **kwargs)

    def reset(self):
        ''' Preset instrument. '''
        self.write("PRES;")
        self.wait_until_finished()

    def wait_until_finished(self):
        self.query("OUTPIDEN;")
