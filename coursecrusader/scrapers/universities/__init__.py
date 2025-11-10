try:
    from .uconn import UconnScraper
except ImportError:
    UconnScraper = None

try:
    from .mit import MitScraper
except ImportError:
    MitScraper = None

try:
    from .yale import YaleScraper
except ImportError:
    YaleScraper = None

try:
    from .stanford import StanfordScraper
except ImportError:
    StanfordScraper = None

try:
    from .berkeley import BerkeleyScraper
except ImportError:
    BerkeleyScraper = None

try:
    from .harvard import HarvardScraper
except ImportError:
    HarvardScraper = None

try:
    from .cornell import CornellScraper
except ImportError:
    CornellScraper = None

try:
    from .princeton import PrincetonScraper
except ImportError:
    PrincetonScraper = None

try:
    from .columbia import ColumbiaScraper
except ImportError:
    ColumbiaScraper = None

try:
    from .upenn import UpennScraper
except ImportError:
    UpennScraper = None

try:
    from .duke import DukeScraper
except ImportError:
    DukeScraper = None

try:
    from .northwestern import NorthwesternScraper
except ImportError:
    NorthwesternScraper = None

try:
    from .dartmouth import DartmouthScraper
except ImportError:
    DartmouthScraper = None

try:
    from .brown import BrownScraper
except ImportError:
    BrownScraper = None

try:
    from .vanderbilt import VanderbiltScraper
except ImportError:
    VanderbiltScraper = None

try:
    from .rice import RiceScraper
except ImportError:
    RiceScraper = None

try:
    from .notre_dame import NotreDameScraper
except ImportError:
    NotreDameScraper = None

try:
    from .ucla import UclaScraper
except ImportError:
    UclaScraper = None

try:
    from .ucsd import UcsdScraper
except ImportError:
    UcsdScraper = None

try:
    from .ucsb import UcsbScraper
except ImportError:
    UcsbScraper = None

try:
    from .uci import UciScraper
except ImportError:
    UciScraper = None

try:
    from .ucd import UcdScraper
except ImportError:
    UcdScraper = None

try:
    from .umich import UmichScraper
except ImportError:
    UmichScraper = None

try:
    from .uva import UvaScraper
except ImportError:
    UvaScraper = None

try:
    from .unc import UncScraper
except ImportError:
    UncScraper = None

try:
    from .georgia_tech import GeorgiaTechScraper
except ImportError:
    GeorgiaTechScraper = None

try:
    from .uiuc import UiucScraper
except ImportError:
    UiucScraper = None

try:
    from .wisconsin import WisconsinScraper
except ImportError:
    WisconsinScraper = None

try:
    from .washington import WashingtonScraper
except ImportError:
    WashingtonScraper = None

try:
    from .utexas import UtexasScraper
except ImportError:
    UtexasScraper = None

try:
    from .usc import UscScraper
except ImportError:
    UscScraper = None

try:
    from .carnegie_mellon import CarnegieMellonScraper
except ImportError:
    CarnegieMellonScraper = None

try:
    from .nyu import NyuScraper
except ImportError:
    NyuScraper = None

try:
    from .boston_u import BostonUScraper
except ImportError:
    BostonUScraper = None

try:
    from .tufts import TuftsScraper
except ImportError:
    TuftsScraper = None

try:
    from .rochester import RochesterScraper
except ImportError:
    RochesterScraper = None

try:
    from .case_western import CaseWesternScraper
except ImportError:
    CaseWesternScraper = None

try:
    from .ohio_state import OhioStateScraper
except ImportError:
    OhioStateScraper = None

try:
    from .penn_state import PennStateScraper
except ImportError:
    PennStateScraper = None

try:
    from .florida import FloridaScraper
except ImportError:
    FloridaScraper = None

try:
    from .purdue import PurdueScraper
except ImportError:
    PurdueScraper = None

try:
    from .rutgers import RutgersScraper
except ImportError:
    RutgersScraper = None

try:
    from .maryland import MarylandScraper
except ImportError:
    MarylandScraper = None

try:
    from .minnesota import MinnesotaScraper
except ImportError:
    MinnesotaScraper = None

try:
    from .pitt import PittScraper
except ImportError:
    PittScraper = None

try:
    from .virginia_tech import VirginiaTechScraper
except ImportError:
    VirginiaTechScraper = None

try:
    from .indiana import IndianaScraper
except ImportError:
    IndianaScraper = None

try:
    from .asu import AsuScraper
except ImportError:
    AsuScraper = None

try:
    from .caltech import CaltechScraper
except ImportError:
    CaltechScraper = None

try:
    from .colorado import ColoradoScraper
except ImportError:
    ColoradoScraper = None

__all__ = ['UconnScraper', 'MitScraper', 'YaleScraper', 'StanfordScraper', 'BerkeleyScraper', 'HarvardScraper', 'CornellScraper', 'PrincetonScraper', 'ColumbiaScraper', 'UpennScraper', 'DukeScraper', 'NorthwesternScraper', 'DartmouthScraper', 'BrownScraper', 'VanderbiltScraper', 'RiceScraper', 'NotreDameScraper', 'UclaScraper', 'UcsdScraper', 'UcsbScraper', 'UciScraper', 'UcdScraper', 'UmichScraper', 'UvaScraper', 'UncScraper', 'GeorgiaTechScraper', 'UiucScraper', 'WisconsinScraper', 'WashingtonScraper', 'UtexasScraper', 'UscScraper', 'CarnegieMellonScraper', 'NyuScraper', 'BostonUScraper', 'TuftsScraper', 'RochesterScraper', 'CaseWesternScraper', 'OhioStateScraper', 'PennStateScraper', 'FloridaScraper', 'PurdueScraper', 'RutgersScraper', 'MarylandScraper', 'MinnesotaScraper', 'PittScraper', 'VirginiaTechScraper', 'IndianaScraper', 'AsuScraper', 'ColoradoScraper', 'CaltechScraper']
