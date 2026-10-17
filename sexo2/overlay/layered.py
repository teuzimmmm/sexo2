"""CPU bitmap surface in our renderer process; no GPU or game calls."""
import ctypes as C
from ctypes import wintypes as W
from PIL import Image, ImageDraw, ImageFont


class LayeredSurface:
    driver = 'cpu'

    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.u = C.WinDLL('user32', use_last_error=True)
        self.g = C.WinDLL('gdi32', use_last_error=True)
        def bind(api, name, result, *args):
            fn = getattr(api, name); fn.restype = result; fn.argtypes = args
        bind(self.u, 'GetDC', W.HDC, W.HWND)
        bind(self.u, 'ReleaseDC', C.c_int, W.HWND, W.HDC)
        bind(self.u, 'UpdateLayeredWindow', W.BOOL, W.HWND, W.HDC, W.LPVOID,
             W.LPVOID, W.HDC, W.LPVOID, W.DWORD, W.LPVOID, W.DWORD)
        bind(self.g, 'CreateCompatibleDC', W.HDC, W.HDC)
        bind(self.g, 'DeleteDC', W.BOOL, W.HDC)
        bind(self.g, 'CreateDIBSection', W.HBITMAP, W.HDC, W.LPVOID, W.UINT,
             C.POINTER(W.LPVOID), W.HANDLE, W.DWORD)
        bind(self.g, 'SelectObject', W.HANDLE, W.HDC, W.HANDLE)
        bind(self.g, 'DeleteObject', W.BOOL, W.HANDLE)
        try:
            self.font = ImageFont.truetype('segoeui.ttf', 16)
        except OSError:
            self.font = ImageFont.load_default(size=16)

    def _text(self, draw, position, value, color, width, height):
        # Draw into a clipped tile so long source text never leaks into gaps.
        tile = Image.new('RGBA', (max(1,width),max(1,height)))
        ImageDraw.Draw(tile).multiline_text((0,0), value, font=self.font, fill=color, spacing=4)
        draw.alpha_composite(tile,position)

    def draw(self, width, height, header, body, footer):
        image = Image.new('RGBA', (width,height), (9,17,25,238))
        self._text(image,(12,8),header,(68,212,191,255),width-24,26)
        if height>40:
            self._text(image,(12,42),body,(226,233,241,255),width-24,height-80)
            self._text(image,(12,height-28),footer,(160,177,189,255),width-24,25)
        self._upload(image)

    def draw_offers(self, width, height, regions):
        if len(regions)!=3:raise ValueError('Three regions required')
        image = Image.new('RGBA',(width,height))
        for x,w,title,body in regions:
            if x<0 or w<1 or x+w>width:raise ValueError('Invalid region')
            tile = Image.new('RGBA',(w,height),(9,17,25,238))
            self._text(tile,(8,4),title,(68,212,191,255),w-16,24)
            if height>28:self._text(tile,(8,28),body,(226,233,241,255),w-16,height-32)
            image.alpha_composite(tile,(x,0))
        self._upload(image)

    def _upload(self,image):
        width,height=image.size
        if not 1<=width<=7680 or not 1<=height<=1140:raise ValueError('Surface dimensions out of range')
        class Header(C.Structure):
            _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),
                      ('bits',W.WORD),('compression',W.DWORD),('imageSize',W.DWORD),
                      ('xppm',W.LONG),('yppm',W.LONG),('colors',W.DWORD),('important',W.DWORD)]
        class Info(C.Structure):
            _fields_=[('header',Header),('colors',W.DWORD*3)]
        class Size(C.Structure):_fields_=[('cx',W.LONG),('cy',W.LONG)]
        class Blend(C.Structure):_fields_=[('op',W.BYTE),('flags',W.BYTE),('alpha',W.BYTE),('format',W.BYTE)]
        dc=self.u.GetDC(None);memory=bitmap=old=None
        if not dc:raise OSError('Desktop DC unavailable')
        try:
            memory=self.g.CreateCompatibleDC(dc)
            info=Info(Header(C.sizeof(Header),width,-height,1,32,0,0,0,0,0,0));bits=W.LPVOID()
            bitmap=self.g.CreateDIBSection(dc,C.byref(info),0,C.byref(bits),None,0)
            if not memory or not bitmap or not bits:raise OSError('Bitmap allocation failed')
            old=self.g.SelectObject(memory,bitmap)
            if old in (None,C.c_void_p(-1).value):raise OSError('Bitmap selection failed')
            pixels=image.convert('RGBa').tobytes('raw','BGRa')
            C.memmove(bits,pixels,len(pixels))
            size=Size(width,height);origin=W.POINT(0,0);blend=Blend(0,0,255,1)
            if not self.u.UpdateLayeredWindow(self.hwnd,dc,None,C.byref(size),memory,
                    C.byref(origin),0,C.byref(blend),2):raise OSError('Layered surface update failed')
        finally:
            if old not in (None,C.c_void_p(-1).value):self.g.SelectObject(memory,old)
            if bitmap:self.g.DeleteObject(bitmap)
            if memory:self.g.DeleteDC(memory)
            self.u.ReleaseDC(None,dc)

    def close(self):pass
