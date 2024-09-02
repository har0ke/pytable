from .types import Adaptation, ColorIntent, ColorSpacesColorProfile, \
    Illuminant, IlluminantLED, ImageOrientation

import struct
import enum

DT_MODULES = []


def decode_bytes(bytes):
    return bytes.decode().rstrip("\0")


class ModuleMeta(type):

    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)
        if name != "Module":
            DT_MODULES.append(new_cls)
        return new_cls


class Module(metaclass=ModuleMeta):

    NAME = ""
    VERSION = -1
    PARAMS_NAMES = ()
    PARAMS_FORMAT = ""
    PARAMS_TYPES = ()

    def __init__(self, instance, raw_params, module_name=None) -> None:
        self.module_name = module_name or self.__class__.__name__
        self.instance = instance
        self.params = self.parse_params(raw_params)

    def parse_params(self, raw_params):
        if not self.PARAMS_FORMAT:
            return {}
        values = struct.unpack(self.PARAMS_FORMAT, raw_params)
        params = {}
        pts = list(self.PARAMS_TYPES) + [None] * (len(self.PARAMS_NAMES) - len(self.PARAMS_TYPES))
        for name, type in zip(self.PARAMS_NAMES, pts):
            n = 1
            if "*" in name:
                name, n = name.split("*")
                n = int(n)
            params[name] = values[:n]
            assert len(params[name]) == n
            if type:
                params[name] = [type(v) for v in params[name]]
            if n == 1:
                params[name] = params[name][0]
            values = values[n:]
        assert not values, values
        return params

    def __str__(self):
        import pprint
        return "%s-%d: %s" % (self.module_name, self.instance, pprint.pformat(
            self.params, indent=0, compact=True, width=10000, depth=1
        ))

    def __repr__(self) -> str:
        return "%s-%d" % (self.module_name, self.instance)

class ColorBalanceRGBSaturation(enum.Enum):
    JZAZBZ = 0
    DTUCS = 1


class ColorBalanceRGB(Module):
    NAME = "colorbalancergb"
    VERSION = 5
    PARAMS_NAMES = ("shadows_Y", "shadows_C", "shadows_H", "midtones_Y",
                    "midtones_C", "midtones_H", "highlights_Y", "highlights_C",
                    "highlights_H", "global_Y", "global_C", "global_H",
                    "shadows_weight", "white_fulcrum", "highlights_weight",
                    "chroma_shadows", "chroma_highlights", "chroma_global",
                    "chroma_midtones", "saturation_global",
                    "saturation_highlights", "saturation_midtones",
                    "saturation_shadows", "hue_angle", "brilliance_global",
                    "brilliance_highlights", "brilliance_midtones",
                    "brilliance_shadows", "mask_grey_fulcrum", "vibrance",
                    "grey_fulcrum", "contrast", "saturation_formula")

    PARAMS_FORMAT = "32fi"
    PARAMS_TYPES = [None] * 32 + [ColorBalanceRGBSaturation]


class ColorCalibrationV2(Module):

    NAME = "channelmixerrgb"
    VERSION = 3
    PARAMS_NAMES = ("red*4", "green*4", "blue*4", "saturation*4",
                    "lightness*4", "grey*4", "normalize_red",
                    "normalize_green", "normalize_blue",
                    "normalize_saturation", "normalize_lightness",
                    "normalize_grey", "illuminant", "illum_fluo",
                    "illum_led", "adaptation", "x", "y", "temperature",
                    "gamut", "clip", "version")
    PARAMS_FORMAT = "24f6i4iffffii"
    PARAMS_TYPES = ([None] * 6 + [bool] * 6 +
                    [Illuminant, None, IlluminantLED, Adaptation,
                     None, None, None, None, bool])


class ColorInputProfileNormalize(enum.Enum):
    OFF = 0
    SRGB = 1
    ADOBE_RGB = 2
    LINEAR_REC709_RGB = 3
    LINEAR_REC2020_RGB = 4


class ColorInputProfileV7(Module):

    NAME = "colorin"
    VERSION = 7
    PARAMS_NAMES = (
        "type", "filename", "intent", "normalize", "blue_mapping", "type_work",
        "filename_work")
    PARAMS_FORMAT = "i512siiii512s"
    PARAMS_TYPES = (ColorSpacesColorProfile, decode_bytes, ColorIntent,
                    ColorInputProfileNormalize, bool, ColorSpacesColorProfile,
                    decode_bytes)


class ColorOutputProfileV5(Module):

    NAME = "colorout"
    VERSION = 5
    PARAMS_NAMES = (
        "type", "filename", "intent")
    PARAMS_FORMAT = "i512si"
    PARAMS_TYPES = (ColorSpacesColorProfile, decode_bytes, ColorIntent)


class ColorZonesChannel(enum.Enum):
    lightness = 0
    chroma = 1
    hue = 2

class ColorZonesV5(Module):
    NAME = "colorzones"
    VERSION = 5
    PARAMS_NAMES = ("channel", "curve*120", "curve_num_nodes*3",
                    "curve_type*3", "strength", "mode", "spline_version")

    PARAMS_FORMAT = "i120f6ifii"

    def parse_params(self, raw_params):
        params = super().parse_params(raw_params)
        curve = params["curve"]
        curve = [
            [(curve[channel * 20 * 2 + node * 2],
              curve[channel * 20 * 2 + node * 2 + 1]) for node in range(20)]
            for channel in range(3)
        ]
        curve[0] = curve[0][:params["curve_num_nodes"][0]]
        curve[1] = curve[1][:params["curve_num_nodes"][1]]
        curve[2] = curve[2][:params["curve_num_nodes"][2]]
        params["curve"] = curve
        return params


class DemosaicMethod(enum.Enum):
    PPG = 0
    AMAZE = 1
    VNG4 = 2
    RCD = 5
    LMMSE = 6
    RCD_VNG = 2048 | 5
    AMAZE_VNG = 2048 | 6
    PASSTHROUGH_MONOCHROME = 3
    PASSTHROUGH_COLOR = 4
    VNG = 1024 | 0
    MARKESTEIJN = 1024 | 1
    MARKESTEIJN_3 = 1024 | 2
    FCD = 1024 | 4
    MARKEST3_VNG = 2048 | 1024 | 2
    PASSTHR_MONOX = 1024 | 3
    PASSTHR_COLORX = 1024 | 5


class DemosaicGreenEQ(enum.Enum):
    NO = 0
    LOCAL = 1
    FULL = 2
    BOTH = 3


class DemosaicQualFlags(enum.Enum):
    DEFAULT = 0
    FULL_SCALE = 1
    ONLY_VNG_LINEAR = 2


class DemosaicSmooth(enum.Enum):
    OFF = 0
    ONCE = 1
    TWICE = 2
    THREE_TIMES = 3
    FOUR_TIMES = 4
    FIVE_TIMES = 5


class DemosaicLMMSE(enum.Enum):
    BASIC = 0
    MEDIAN = 1
    MEDIANX3 = 2
    REFINE_AND_MEDIANS = 3
    REFINEx2_AND_MEDIANS = 4


class DemosaicV4(Module):

    NAME = "demosaic"
    VERSION = 4
    PARAMS_NAMES = (
        "green_eq", "median_thrs", "color_smoothing", "demosaicing_method",
        "lmmse_refine", "dual_thrs")
    PARAMS_FORMAT = "ifiiif"
    PARAMS_TYPES = (DemosaicGreenEQ, None, DemosaicSmooth, DemosaicMethod, DemosaicLMMSE)


class DenoiseProfiledWaveletMode(enum.Enum):
    RGB = 0
    Y0U0V0 = 1

class DenoiseProfiled(Module):
    NAME = "denoiseprofile"
    VERSION = 11
    PARAMS_NAMES = ("radius", "nbhood", "strength", "shadows",
                    "bias", "scattering", "central_pixel_weight",
                    "overshooting", "a*3", "b*3", "mode", "x*42", "y*42",
                    "wb_adaptive_anscombe", "fix_anscombe_and_nlmeans_norm",
                    "use_new_vst", "wavelet_color_mode")

    PARAMS_FORMAT = "8f6fi42f42fiiii"
    PARAMS_TYPES = [None] * 16 + [DenoiseProfiledWaveletMode]

    def parse_params(self, raw_params):
        params = super().parse_params(raw_params)
        params["x"] = [[params["x"][profile * 7 + band] for band in range(7)] for profile in range(6)]
        params["y"] = [[params["y"][profile * 7 + band] for band in range(7)] for profile in range(6)]
        return params


class DiffuseOrSharpenV2(Module):

    NAME = "diffuse"
    VERSION = 2
    PARAMS_NAMES = (
        "iterations", "sharpness", "radius", "regularization",
        "variance_threshold", "anisotropy_first", "anisotropy_second",
        "anisotropy_third", "anisotropy_fourth", "threshold",
        "first", "second", "third", "fourth", "radius_center")
    PARAMS_FORMAT = "ififffffffffffi"


class DisplayEncodingV1(Module):

    NAME = "gamma"
    VERSION = 1
    PARAMS_NAMES = ("gamma", "linear")
    PARAMS_FORMAT = "ff"


class ExposureMode(enum.Enum):
    MANUAL = 0
    DEFLICKER = 1


class ExposureV6(Module):

    NAME = "exposure"
    VERSION = 6
    PARAMS_NAMES = ("mode", "black", "exposure", "deflicker_percentile",
                    "deflicker_target_level", "compensate_exposure_bias")
    PARAMS_FORMAT = "iffffi"
    PARAMS_TYPES = (ExposureMode, None, None, None, None, bool)


class FilmicRGBMethod(enum.Enum):
    NONE = 0
    MAX_RGB = 1
    LUMINANCE = 2
    POWER_NORM = 3
    EUCLIDEAN_NORM_V1 = 4
    EUCLIDEAN_NORM_V2 = 5


class FilmicRGBCurve(enum.Enum):
    POLY_4 = 0
    POLY_3 = 1
    RATIONAL = 2


class FilmicRGBReconstruction(enum.Enum):
    RECONSTRUCT_RGB = 0
    RECONSTRUCT_RATIOS = 1


class FilmicRGBNoiseDistribution(enum.Enum):
    UNIFORM = 0
    GAUSSIAN = 1
    POISSONIAN = 2


class FilmicRGB(Module):

    NAME = "filmicrgb"
    VERSION = 6
    PARAMS_NAMES = ("grey_point_source", "black_point_source",
                    "white_point_source", "reconstruct_threshold",
                    "reconstruct_feather", "reconstruct_bloom_vs_details",
                    "reconstruct_grey_vs_color",
                    "reconstruct_structure_vs_texture", "security_factor",
                    "grey_point_target", "black_point_target",
                    "white_point_target", "output_power", "latitude",
                    "contrast", "saturation", "balance", "noise_level",
                    "preserve_color", "version", "auto_hardness", "custom_grey",
                    "high_quality_reconstruction", "noise_distribution",
                    "shadows", "highlights", "compensate_icc_black",
                    "spline_version", "enable_highlight_reconstruction")
    PARAMS_FORMAT = "18f11i"
    PARAMS_TYPES = [None] * 18 + [
        FilmicRGBMethod, None, bool, bool, None, FilmicRGBNoiseDistribution,
        FilmicRGBCurve, FilmicRGBCurve, bool, None, bool]


class HighlightsMode(enum.Enum):
    OPPOSED = 5
    LCH = 1
    CLIP = 0
    SEGMENTS = 4
    LAPLACIAN = 3
    INPAINT = 2

class HighlightsAtrousWaveletsScales(enum.Enum):
    PX2 = 0
    PX4 = 1
    PX8 = 2
    PX16 = 3
    PX32 = 4
    PX64 = 5
    PX128 = 6
    PX256 = 7
    PX512 = 8
    PX1024 = 9
    PX2048 = 10
    PX4096 = 11

class HighlightsRecoveryMode(enum.Enum):
    MODE_OFF = 0
    MODE_ADAPT = 5
    MODE_ADAPTF = 6
    MODE_SMALL = 1
    MODE_LARGE = 2
    MODE_SMALLF = 3
    MODE_LARGEF = 4


class HighlightsV4(Module):

    NAME = "highlights"
    VERSION = 4
    PARAMS_NAMES = ("mode", "blendL", "blendC", "strength", "clip",
                    "noise_level", "iterations", "scales", "candidating",
                    "combine", "recovery", "solid_color")
    PARAMS_FORMAT = "ifffffiiffif"
    PARAMS_TYPES = (HighlightsMode, None, None, None, None, None, None,
                    HighlightsAtrousWaveletsScales, None, None,
                    HighlightsRecoveryMode)


class LocalContrastMode(enum.Enum):
    BILATERAL = 0
    LOCAL_LAPLACIAN = 1

class LocalContrastV3(Module):
    NAME = "bilat"
    VERSION = 3
    PARAMS_NAMES = ("mode", "sigma_r", "sigma_s", "detail", "midtone")
    PARAMS_FORMAT = "i4f"
    PARAMS_TYPES = (LocalContrastMode,)


class OrientationV2(Module):
    NAME = "flip"
    VERSION = 2
    PARAMS_NAMES = ("orientation",)
    PARAMS_FORMAT = "i"
    PARAMS_TYPES = (ImageOrientation,)


class SharpenV1(Module):
    NAME = "sharpen"
    VERSION = 1
    PARAMS_NAMES = ("radius", "amount", "threshold")
    PARAMS_FORMAT = "3f"


class RawBlackWhitePointV2(Module):

    NAME = "rawprepare"
    VERSION = 2
    PARAMS_NAMES = (
        "left", "top", "right", "bottom", "raw_black_level_separate0",
        "raw_black_level_separate1", "raw_black_level_separate2",
        "raw_black_level_separate3", "raw_white_point", "flat_field")
    PARAMS_FORMAT = "iiiiHHHHHi"


class WhiteBalance(Module):

    NAME = "temperature"
    VERSION = 3
    PARAMS_NAMES = ("red", "green", "blue", "g2")
    PARAMS_FORMAT = "ffff"
