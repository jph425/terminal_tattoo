#!/usr/bin/env python
#
# terminal_tattoo.py
#
# Renders an image as specified
# (c) Copyright 2021, Jamie Harding. All rights reserved.

from PIL import Image, ImageDraw, ImageFont
import argparse
import logging
import tempfile
from os import path, get_terminal_size
from sys import exit
import pprint
import re

DEFAULT_FONT = '/System/Library/Fonts/Menlo.ttc'
DEFAULT_SIZE = 45
DEFAULT_POS  = 'tR' # top right corner
DEFAULT_FGC  = 'fK' # black
DEFAULT_BGC  = 'bW' # white

POSITION_CODES = ['pT', 'pTL', 'pTR', 'pB', 'pBL', 'pBR', 'pC', 'pL', 'pR']

RETINA_HCELL_PIXELS = 14
RETINA_VCELL_PIXELS = 28
RETINA_H_OFFSET     = 20
RETINA_V_OFFSET     = 14

EXIT_INVALID_FG   = -1
EXIT_INVALID_BG   = -2
EXIT_DOES_NOT_FIT = -3

##############################################################################
# logging stuff:
##############################################################################
class ColorizingStreamHandler(logging.StreamHandler):
    @property
    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)
        return isatty

    def emit(self, record):
        # noinspection PyBroadException
        try:
            message = self.format(record)
            stream = self.stream
            if not self.is_tty:
                stream.write(message)
            else:
                self.output_colorized(message)
            stream.write(getattr(self, 'terminator', '\n'))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        if self.is_tty:
            # Don't colorize traceback
            parts = message.split('\n', 1)
            parts[0] = self.colorize(parts[0], record)
            message = '\n'.join(parts)
        return message

    # color names to partial ANSI code (there'll be math later to make complete codes)
    color_map = {
        'black':   0,
        'red':     1,
        'green':   2,
        'yellow':  3,
        'blue':    4,
        'magenta': 5,
        'cyan':    6,
        'white':   7,
    }

    # logging levels to (background, foreground, intense)
    # NOT multi-platform!
    level_map = {
        logging.DEBUG:    (None,  'blue',   False),
        logging.INFO:     (None,  'black',  False),
        logging.WARNING:  (None,  'yellow', False),
        logging.ERROR:    (None,  'red',    True),
        logging.CRITICAL: ('red', 'white',  True),
    }

    csi = '\x1b['
    reset = '\x1b[0m'

    def colorize(self, message, record):
        if record.levelno in self.level_map:
            bg, fg, bold = self.level_map[record.levelno]
            params = []
            if bg in self.color_map:
                params.append(str(self.color_map[bg] + 40))
            if fg in self.color_map:
                params.append(str(self.color_map[fg] + 30))
            if bold:
                params.append('1')
            if params:
                message = ''.join((self.csi, ';'.join(params), 'm', message, self.reset))
        return message

    def output_colorized(self, message):
        self.stream.write(message)
# End Class ColorizingStreamHandler


# Initialize logging objects
Logger = logging.getLogger("terminal_tattoo")

formatter = logging.Formatter('%(levelname)-10s: %(message)s')
handler = ColorizingStreamHandler()

handler.setFormatter(formatter)
Logger.addHandler(handler)

pp = pprint.PrettyPrinter(indent=4)

##############################################################################
# main:
##############################################################################

def main():
    parser = config_parser()
    args = parser.parse_args()

    if None == args.verbose:
        Logger.setLevel(logging.ERROR)
        handler.setLevel(logging.ERROR)
    else:
        if args.verbose > 0:
            Logger.setLevel(logging.WARNING)
            handler.setLevel(logging.WARNING)
        if args.verbose > 1:
            Logger.setLevel(logging.INFO)
            handler.setLevel(logging.INFO)
        if args.verbose > 2:
            Logger.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)
            Logger.debug("parsed args:")
            pp.pprint(args)

    (c, l) = get_terminal_size()
    (w, h) = get_terminal_pixel_size(c, l, RETINA_HCELL_PIXELS, RETINA_VCELL_PIXELS, RETINA_H_OFFSET, RETINA_V_OFFSET)

    position = check_position(args)
    fg_color = check_fg_color(args)
    bg_color = check_bg_color(args)
    out_path = check_output_file(args)
    font = check_font(args)
    text = ' '.join(args.text)
    size = check_size(args)
    alpha = check_alpha(args)
    margin = check_margin(args)

    render_bg_image = create_image(w, h, html_to_888(bg_color))
    render_font = create_font(font, size)
    (render_text_width, render_text_height) = get_text_dimensions(render_font, text)

    if not fit_check(render_text_width, render_text_height, margin, w, h):
        exit(EXIT_DOES_NOT_FIT)

    return

##############################################################################
# other functions:
##############################################################################

def html_to_888(html_str):
    pat = r'(?P<red>[0-9a-fA-F]{2})(?P<green>[0-9a-fA-F]{2})(?P<blue>[0-9a-fA-F]{2})'
    m = re.match(pat, html_str)
    r = hex_byte_to_int(m.group('red'))
    g = hex_byte_to_int(m.group('green'))
    b = hex_byte_to_int(m.group('blue'))
    Logger.debug("converted color #{} to RGB888 ({}, {}, {})".format(html_str, r, g, b))
    return (r,g,b)

def hex_byte_to_int(hexbyte_string):
    return int(hexbyte_string, 16)

def get_text_dimensions(font_obj, text):
    (w, h) = font_obj.getsize(text)
    Logger.debug("measured size of text (\'{}\') is ({}, {})".format(text, w, h))
    return (w, h)

def get_text_anchor_pos(pos, text_w, text_h, image_w, image_h):
    """the text anchor is (by default in ImageFont) the top left corner of the
    bounding box. I see no reason to change this. The math is trivial when we
    know the desired text location in the image, the image width and height,
    and the text width and height."""

    return

def check_margin(args):
    return

def create_font(font_name, size):
    return ImageFont.truetype(font_name, size)

def create_image(w, h, blanking_color):
    image = Image.new('RGBA', (w, h), blanking_color)
    return image

def composite_text():
    return

def fit_check(render_text_width, render_text_height, margin, w, h):
    return

def get_terminal_dimensions():
    ts = get_terminal_size()
    columns = ts.columns
    lines = ts.lines
    Logger.debug("terminal character cell dimensions measured at ({}, {})".format(columns, lines))
    return (columns, lines)

def get_terminal_pixel_size(columns, lines, h_pix, v_pix, h_offset=0, v_offset=0):
    height = lines * v_pix + v_offset
    width = columns * h_pix + h_offset
    Logger.info("terminal dimensions: width: {} height: {}".format(width, height))
    return (width, height)

def check_position(args):
    ret = DEFAULT_POS
    position_args = POSITION_CODES
    for p in position_args:
        if p in args:
            ret = p
            break
    Logger.info("position will be {}".format(ret))
    return ret

def check_fg_color(args):
    ret = DEFAULT_FGC
    skip_iter = False
    if args.f is not None:
        if validate_html_color(args.b):
            Logger.debug("the detected bg color is {}".format(args.b))
            ret = args.b
        else:
            Logger.error("invalid bg color format given, a 6-digit hex value is required (HTML format)")
            exit(EXIT_INVALID_FG)
    color_args = ['f', 'fR', 'fG', 'fB', 'fW', 'fK', 'fC', 'fM', 'fY', 'fg']
    color_in_hex = {'fR': 'FF0000', 'fG': '00FF00', 'ff': '0000FF', 'fW': 'FFFFFF', 'fK': '000000', 'fC': '00FFFF', 'fM': 'FF00ff', 'fY': 'FFFF00', 'fg': 'A9A9A9'}
    if not skip_iter:
        for color in color_args:
            if getattr(args, color) == True:
                Logger.debug("the detected fg color is: {}".format(color))
                ret = color_in_hex[color]
    Logger.info("background color will be {}".format(ret))
    ret = sanitize_html_color(ret)
    return ret

def check_bg_color(args):
    ret = DEFAULT_BGC
    skip_iter = False
    if args.b is not None:
        if validate_html_color(args.b):
            Logger.debug("the detected bg color is {}".format(args.b))
            ret = args.b
        else:
            Logger.error("invalid bg color format given, a 6-digit hex value is required (HTML format)")
            exit(EXIT_INVALID_BG)
    color_args = ['bR', 'bG', 'bB', 'bW', 'bK', 'bC', 'bM', 'bY', 'bg']
    color_in_hex = {'bR': 'FF0000', 'bG': '00FF00', 'bB': '0000FF', 'bW': 'FFFFFF', 'bK': '000000', 'bC': '00FFFF', 'bM': 'FF00ff', 'bY': 'FFFF00', 'bg': 'A9A9A9'}
    if not skip_iter:
        for color in color_args:
            if getattr(args, color) == True:
                Logger.debug("the detected bg color is: {}".format(color))
                ret = color_in_hex[color]
    Logger.info("background color will be {}".format(ret))
    ret = sanitize_html_color(ret)
    return ret

def check_alpha(args):
    a = args.alpha
    if a > 255:
        a = 255
        Logger.info("clamping alpha to 255")
    elif a < 0:
        a = 0
        Logger.info("clamping alpha to 0 (what are you doing?)")
    else:
        Logger.info("alpha will be {}".format(a))
    return a

def validate_html_color(color):
    ret = False
    pattern = r'[#]?[0-9a-fA-F]{6}'
    m = re.search(pattern, color)
    if m.group(0) == color:
        ret = True
    return ret

def sanitize_html_color(code):
    m = re.match(r'[#]?([0-9a-fA-F]{6})', code)
    Logger.debug("santized html code {} to {}".format(code, m.group(1)))
    return m.group(1)

def check_output_file(args):
    if not args.out_path:
        fallback = tempfile.NamedTemporaryFile(dir='/tmp/')
        fallback.close() # heh, gross hack to just get some random path
        ret = fallback.name + '.png'
    else:
        ret = args.out_path
    Logger.info("Output file for image is {}".format(ret))
    return ret

def check_font(args):
    ret = False
    if args.font:
        if path.exists(args.font):
            (_, file_extension) = path.splitext(args.font)
            if file_extension == '.ttf' or file_extension == '.ttc':
                ret = True
    if ret:
        ret = args.font
    else:
        ret = DEFAULT_FONT
    Logger.info("font will be {}".format(ret))
    return ret

def check_size(args):
    ret = DEFAULT_SIZE
    if args.s:
        ret = args.s
    Logger.info("text will be point size {}".format(ret))
    return ret

def config_parser():
    parser = argparse.ArgumentParser(description='Render an image for a watermarked Terminal window.', \
        epilog='Defaults to {}, size {}, black text on white, positioned in the top right corner.'.format(path.basename(DEFAULT_FONT), DEFAULT_SIZE))
    parser.add_argument('text', type=str, nargs='+', help='Text to use in the watermark')
    parser.add_argument('-s', metavar='SIZE', type=int, help='point size of the text')
    parser.add_argument('--font', metavar='PATH', help='font to use for the watermark')
    parser.add_argument('--verbose', '-v', action='count', help='verbose mode (can be repeated)', default=0)
    parser.add_argument('-o', metavar='PATH', dest='out_path', help='output file for the rendered image')
    parser.add_argument('--alpha', '-a', type=int, metavar='ALPHA', default=255, help='alpha value of text')

    position = parser.add_mutually_exclusive_group()
    position.add_argument('--pT',  action='store_true', help='top center')
    position.add_argument('--pTL', action='store_true', help='top left')
    position.add_argument('--pTR', action='store_true', help='top right')
    position.add_argument('--pB',  action='store_true', help='bottom center')
    position.add_argument('--pBL', action='store_true', help='bottom left')
    position.add_argument('--pBR', action='store_true', help='bottom right')
    position.add_argument('--pC',  action='store_true', help='center')
    position.add_argument('--pL',  action='store_true', help='left center')
    position.add_argument('--pR',  action='store_true', help='right center')

    parser.add_argument('--margin', default=25, help='no-text perimeter width')

    fgColor = parser.add_mutually_exclusive_group()
    fgColor.add_argument('--fR', action='store_true', help='red')
    fgColor.add_argument('--fG', action='store_true', help='green')
    fgColor.add_argument('--fB', action='store_true', help='blue')
    fgColor.add_argument('--fW', action='store_true', help='white')
    fgColor.add_argument('--fK', action='store_true', help='black')
    fgColor.add_argument('--fC', action='store_true', help='cyan')
    fgColor.add_argument('--fM', action='store_true', help='magenta')
    fgColor.add_argument('--fY', action='store_true', help='yellow')
    fgColor.add_argument('--fg', action='store_true', help='medium gray')
    fgColor.add_argument('--f', metavar='NNNNNN', help='arbitrary color in HTML format')

    bgColor = parser.add_mutually_exclusive_group()
    bgColor.add_argument('--bR', action='store_true', help='red')
    bgColor.add_argument('--bG', action='store_true', help='green')
    bgColor.add_argument('--bB', action='store_true', help='blue')
    bgColor.add_argument('--bW', action='store_true', help='white')
    bgColor.add_argument('--bK', action='store_true', help='black')
    bgColor.add_argument('--bC', action='store_true', help='cyan')
    bgColor.add_argument('--bM', action='store_true', help='magenta')
    bgColor.add_argument('--bY', action='store_true', help='yellow')
    bgColor.add_argument('--bg', action='store_true', help='medium gray')
    bgColor.add_argument('--b', metavar='NNNNNN', help='arbitrary color in HTML format')

    return parser

if __name__ == '__main__':
    main()