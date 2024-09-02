import enum


class Adaptation(enum.Enum):
    LINEAR_BRADFORD = 0
    CAT16           = 1
    FULL_BRADFORD   = 2
    XYZ             = 3
    RGB             = 4


class ColorSpacesColorProfile(enum.Enum):
    NONE = -1
    FILE = 0
    SRGB = 1
    ADOBERGB = 2
    LIN_REC709 = 3
    LIN_REC2020 = 4
    XYZ = 5
    LAB = 6
    INFRARED = 7
    DISPLAY = 8
    EMBEDDED_ICC = 9
    EMBEDDED_MATRIX = 10
    STANDARD_MATRIX = 11
    ENHANCED_MATRIX = 12
    VENDOR_MATRIX = 13
    ALTERNATE_MATRIX = 14
    BRG = 15
    EXPORT = 16
    SOFTPROOF = 17
    WORK = 18
    DISPLAY2 = 19
    REC709 = 20
    PROPHOTO_RGB = 21
    PQ_REC2020 = 22
    HLG_REC2020 = 23
    PQ_P3 = 24
    HLG_P3 = 25
    LAST = 26


class ColorIntent(enum.Enum):
    PERCEPTUAL = 0
    RELATIVE_COLORIMETRIC = 1
    SATURATION = 2
    ABSOLUTE_COLORIMETRIC = 3


class Illuminant(enum.Enum):
    PIPE            = 0
    A               = 1
    D               = 2
    E               = 3
    F               = 4
    LED             = 5
    BB              = 6
    CUSTOM          = 7
    DETECT_SURFACES = 8
    DETECT_EDGES    = 9
    CAMERA          = 10


class IlluminantLED(enum.Enum):
    LED_B1  = 0
    LED_B2  = 1
    LED_B3  = 2
    LED_B4  = 3
    LED_B5  = 4
    LED_BH1 = 5
    LED_RGB1= 6
    LED_V1  = 7
    LED_V2  = 8


class IOPOrderType(enum.Enum):
  CUSTOM  = 0
  LEGACY  = 1
  V30     = 2
  V30_JPG = 3

class Color(enum.Enum):
    RED = 0
    YELLOW = 1
    GREEN = 2
    BLUE = 3
    PURPLE = 4

class ImageFlags(enum.Enum):
    """
    Flags that are stored in Image::flags. Extract flags with 'image.flag(flag)'

    Extracted from:
    https:  """
    # Image is rejected
    REJECTED = 8
    THUMBNAIL_DEPRECATED = 16
    # set during import if the image is low-dynamic range, i.e. doesn't
    # need demosaic, wb, highlight clipping etc.
    LDR = 32,
    # set during import if the image is raw data, i.e. it needs demosaicing.
    RAW = 64
    # set during import if images is a high-dynamic range image..
    HDR = 128
    # set when marked for deletion
    REMOVE = 256
    # set when auto-applying presets have been applied to this image.
    AUTO_PRESETS_APPLIED = 512
    # legacy flag. is set for all new images. i hate to waste a bit on this :(
    NO_LEGACY_PRESETS = 1024
    # local copy status
    LOCAL_COPY = 2048
    # image has an associated .txt file for overlay
    HAS_TXT = 4096
    # image has an associated wav file
    HAS_WAV = 8192
    # image is a bayer pattern with 4 colors (e.g., CYGM or RGBE)
    BAYER = 16384
    # image was detected as monochrome
    MONOCHROME = 32768
    # DNG image has exif tags which are not cached in the database but
    # must be read and stored in t when the image is loaded.
    HAS_ADDITIONAL_EXIF_TAGS = 65536
    # image is an sraw
    S_RAW = 1 << 17
    # image has a monochrome preview tested
    MONOCHROME_PREVIEW = 1 << 18
    # image has been set to monochrome via demosaic module
    MONOCHROME_BAYER = 1 << 19
    # image has a flag set to use the monochrome workflow in the modules supporting it
    MONOCHROME_WORKFLOW = 1 << 20

class ImageOrientation(enum.Enum):
    NULL    = -1
    NONE    = 0
    FLIP_Y  = 1 << 0
    FLIP_X  = 1 << 1
    SWAP_XY = 1 << 2
    FLIP_HORIZONTALLY = FLIP_X
    FLIP_VERTICALLY   = FLIP_Y
    ROTATE_180_DEG    = FLIP_Y | FLIP_X
    TRANSPOSE         = SWAP_XY
    ROTATE_CCW_90_DEG = FLIP_X | SWAP_XY
    ROTATE_CW_90_DEG  = FLIP_Y | SWAP_XY
    TRANSVERSE        = FLIP_Y | FLIP_X | SWAP_XY


legacy_order = (
  "rawprepare", "invert", "temperature", "highlights", "cacorrect",
  "hotpixels", "rawdenoise", "demosaic", "mask_manager", "denoiseprofile",
  "tonemap", "exposure", "spots", "retouch", "lens", "cacorrectrgb", "ashift",
  "liquify", "rotatepixels", "scalepixels", "flip", "clipping", "toneequal",
  "crop", "graduatednd", "basecurve", "bilateral", "profile_gamma",
  "hazeremoval", "colorin", "channelmixerrgb", "diffuse", "censorize",
  "negadoctor", "blurs", "basicadj", "colorreconstruct", "colorchecker",
  "defringe", "equalizer", "vibrance", "colorbalance", "colorbalancergb",
  "colorize", "colortransfer", "colormapping", "bloom", "nlmeans",
  "globaltonemap", "shadhi", "atrous", "bilat", "colorzones", "lowlight",
  "monochrome", "sigmoid", "filmic", "filmicrgb", "colisa", "zonesystem",
  "tonecurve", "levels", "rgblevels", "rgbcurve", "relight", "colorcorrection",
  "sharpen", "lowpass", "highpass", "grain", "lut3d", "colorcontrast",
  "colorout", "channelmixer", "soften", "vignette", "splittoning", "velvia",
  "clahe", "finalscale", "overexposed", "rawoverexposed", "dither", "borders",
  "watermark", "gamma"
)

v30_order = (
  "rawprepare", "invert", "temperature", "highlights", "cacorrect", "hotpixels",
  "rawdenoise", "demosaic", "denoiseprofile", "bilateral", "rotatepixels",
  "scalepixels", "lens", "cacorrectrgb","hazeremoval", "ashift", "flip",
  "clipping", "liquify", "spots", "retouch", "exposure", "mask_manager",
  "tonemap", "toneequal","crop","graduatednd", "profile_gamma", "equalizer",
  "colorin", "channelmixerrgb", "diffuse", "censorize", "negadoctor","blurs",
  "nlmeans","colorchecker","defringe","atrous", "lowpass", "highpass", "sharpen",
  "colortransfer","colormapping", "channelmixer","basicadj", "colorbalance",
  "colorbalancergb", "rgbcurve", "rgblevels", "basecurve","filmic", "sigmoid",
   "filmicrgb", "lut3d", "colisa", "tonecurve", "levels", "shadhi",
   "zonesystem", "globaltonemap", "relight", "bilat","colorcorrection",
   "colorcontrast", "velvia", "vibrance", "colorzones", "bloom", "colorize",
   "lowlight", "monochrome", "grain", "soften", "splittoning", "vignette",
   "colorreconstruct", "colorout", "clahe", "finalscale", "overexposed",
   "rawoverexposed", "dither", "borders", "watermark", "gamma"
)

v30_jpg_order = (
  "rawprepare", "invert", "temperature", "highlights", "cacorrect", "hotpixels",
  "rawdenoise", "demosaic", "colorin", "denoiseprofile", "bilateral",
  "rotatepixels", "scalepixels", "lens", "cacorrectrgb", "hazeremoval",
  "ashift", "flip", "clipping", "liquify", "spots", "retouch", "exposure",
  "mask_manager", "tonemap", "toneequal", "crop", "graduatednd",
  "profile_gamma", "equalizer", "channelmixerrgb", "diffuse", "censorize",
  "negadoctor", "blurs", "nlmeans", "colorchecker","defringe","atrous",
  "lowpass", "highpass", "sharpen", "colortransfer","colormapping",
  "channelmixer","basicadj", "colorbalance", "colorbalancergb", "rgbcurve",
  "rgblevels", "basecurve","filmic", "sigmoid", "filmicrgb", "lut3d", "colisa",
  "tonecurve", "levels", "shadhi", "zonesystem", "globaltonemap", "relight",
  "bilat","colorcorrection","colorcontrast", "velvia", "vibrance",
  "colorzones", "bloom", "colorize", "lowlight", "monochrome", "grain",
  "soften", "splittoning", "vignette", "colorreconstruct","colorout", "clahe",
  "finalscale", "overexposed", "rawoverexposed", "dither", "borders",
  "watermark", "gamma"
)
