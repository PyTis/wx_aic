import time

import wx
from wx.lib.newevent import NewCommandEvent
import pytweening as ptw

from aic import ActiveImageControl

ss_cmd_event, EVT_SS_CHANGE = NewCommandEvent()


class SingleSlider(ActiveImageControl):

    def __init__(self, parent, bitmaps, isvertical=False, *args, **kwargs):
        """
        An Image Control for presenting a rotary dial style, (eg a knob or dial type control)
        It behaves similarly to a native control slider, except value is expressed as degrees (float)

        :param bitmaps:  wx.BitMap objects - iterable
                        (first bitmap will be the static background)
                        (the second will be the handle (pointer), preferably smaller than the static bitmap
                        If the handle is larger, you may need to compensate by adding padding to the slider
        """

        super().__init__(parent, *args, **kwargs)
        # No borders + Wants Chars - to grab (cursor) key input
        self.SetWindowStyleFlag(wx.NO_BORDER | wx.WANTS_CHARS)

        self.parent = parent
        self.index = isvertical     # index is 0 for horizontal layout, 1 for vertical layout
        self.stat_bmp = bitmaps[0]
        self._stat_size = self.stat_bmp.Size
        self._stat_padding = (10, 10)
        self._stat_position = wx.Point(self.GetPosition() + self._stat_padding)

        self.handle_bmp = bitmaps[1]
        self._handle_size = self.handle_bmp.Size
        self._handle_offset = (0, 0)  # x,y offset for positioning handle relative to the zero position
        self._handle_centre = rect_centre(self._handle_size)
        self._handle_default = wx.Point(0, 0)
        self._handle_max_pos = wx.Point(self._stat_size[0],
                                        self._stat_size[1])  # max position relative to zero position
        self._handle_pos = wx.Point(self._handle_offset)  # handle top-left point

        self._scroll_step = 1
        self._key_step = 1

        self.highlight_box = ((0, 0), (0, 0))

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.on_paint)

        self.Bind(wx.EVT_KEY_DOWN, self.on_keypress)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_MIDDLE_UP, self.on_middle_up)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_left_drag)

    # Class overrides #
    def DoGetBestSize(self):
        w, h = self._stat_size
        pad_x, pad_y = self._stat_padding
        size = wx.Size(w + pad_x * 2, h + pad_y * 2)
        return size

    # Event handling #
    def on_paint(self, _):
        window_rect = self.GetRect()
        # print(window_rect)
        buffer_bitmap = self.parent.bg_render.GetSubBitmap(window_rect)
        self.draw_to_context(wx.BufferedPaintDC(self, buffer_bitmap))

    def draw_to_context(self, dc):
        dc.DrawBitmap(self.stat_bmp, self._stat_position)
        handle_pos = self._handle_pos[0] + self._stat_position[0], self._handle_pos[1] + self._stat_position[1]
        dc.DrawBitmap(self.handle_bmp, handle_pos)

        if self.highlight and self.HasFocus():
            self.draw_highlight(dc, self.GetSize(), self.highlight_box)

    def on_keypress(self, event):
        if self.HasFocus():
            keycode = event.GetKeyCode()
            index = self.index
            if keycode in [wx.WXK_RIGHT, wx.WXK_UP]:
                handle_pos = self._handle_pos[index] + self._key_step
                self.move_handle(handle_pos)
            elif keycode in [wx.WXK_LEFT, wx.WXK_DOWN]:
                handle_pos = self._handle_pos[index] - self._key_step
                self.move_handle(handle_pos)
            elif keycode == wx.WXK_SPACE:
                self.reset_position()
            elif keycode == wx.WXK_TAB:
                self.Navigate(not (event.ShiftDown()))  # Navigates backwards if 'shift' key is held
        event.Skip()

    def on_mouse_wheel(self, event):
        if not self.HasFocus():
            self.SetFocus()
        index = self.index
        delta = event.GetWheelDelta()  # usually +/-120, but it's better not to assume
        handle_pos = self._handle_pos[index] + (self._scroll_step * event.GetWheelRotation() // delta)
        self.move_handle(handle_pos)

    def on_left_down(self, event):
        self.mouse_move(event.GetPosition())

    def on_left_drag(self, event):
        if event.Dragging() and event.LeftIsDown():
            self.mouse_move(event.GetPosition())
        event.Skip()

    def mouse_move(self, mouse_pos):
        if not self.HasFocus():
            self.SetFocus()
        index = self.index
        handle_pos = mouse_pos[index] - self._handle_centre[index] - self._stat_padding[index]
        self.move_handle(handle_pos)

    def move_handle(self,pos):
        if self.index:
            self.set_position((self._handle_pos[0], pos))
        else:
            self.set_position((pos, self._handle_pos[1]))

    def on_middle_up(self, _):
        if not self.HasFocus():
            self.SetFocus()
        self.reset_position()

    # Getters and Setters #
    def set_padding(self, padding=(0, 0)):
        """ Apply additional padding around the static image, mouse events will extend into the padding """
        self._stat_padding = padding
        self._stat_position = self.GetPosition() + self._stat_padding

    def set_default_pos(self, pos=(0, 0)):
        """ Set the default position for the handle, resetting will place the handle at this point"""
        self.set_position(pos)
        if 0 <= pos[0] <= self._stat_size[0]:  # checks for less than zero and great than the image width
            self.set_position(pos)
            self._handle_default = self._handle_pos
        else:
            raise ValueError('The position value is not within the boundary of the slider widget')

    def set_max(self, pos=(0, 0)):
        if 0 <= pos[0] <= self._stat_size[0]:  # checks for less than zero and great than the image width
            self._handle_max_pos = pos
        else:
            raise ValueError('The position value is not within the boundary of the slider widget')

    def set_offset(self, pos=(0, 0)):
        if (0 <= pos[0] <= self._stat_size[0]) and (0 <= pos[1] <= self._stat_size[1]):
            self._handle_offset = pos
        else:
            raise ValueError('The position value is not within the boundary of the slider widget')

    def set_step(self, scroll=1.0, key=1.0):
        """ Set the increment value (in degrees) for the scroll-wheel and cursor keys"""
        self.set_scroll_step(scroll)
        self.set_key_step(key)

    def set_scroll_step(self, step=1.0):
        """ Set the scroll-wheel step size (float > 0) """
        self._scroll_step = step

    def set_key_step(self, step=1.0):
        """ Set key step size (float > 0) """
        self._key_step = step

    def set_position(self, pos=(0, 0)):
        """ Parse and Set the (actual pixel) position for the handle """
        parsed_pos = self._parse_limits(pos, self._handle_max_pos)
        if parsed_pos != self._handle_pos:
            self._handle_pos = parsed_pos
            wx.PostEvent(self, ss_cmd_event(id=self.GetId(), state=self.value))
            self._refresh()

    def reset_position(self, animate=True):
        self._animate(self._handle_default, animate)

    # Properties #
    @property
    def value(self):
        value = self._handle_pos[self.index] / self._handle_max_pos[self.index]
        return value  # as percentage

    @value.setter
    def value(self, percent):
        if self.index:
            self.set_position((self._handle_max_pos[0], percent * self._handle_max_pos[1]))
        else:
            self.set_position((percent * self._handle_max_pos[0], self._handle_max_pos[1]))

    # Helper methods #
    def _refresh(self):
        self.Refresh(True)  # because we use the full length of the control, we refresh the whole window

    def _animate(self, destination, animate=True):
        if not animate:
            self.set_position(destination)
        else:
            index = self.index
            curr_pos = self._handle_pos[index]  # for horizontal movement, [1] for vertical...
            max_pos = self._handle_max_pos[index]
            def_pos = destination[index]
            diff = def_pos - curr_pos
            if diff:
                step = 4 * int(diff / abs(diff))
                # start = time.perf_counter()
                for i in range(curr_pos, def_pos, step):
                    self.move_handle(i)
                    # because we are using sleep in a loop, we are not returning control to the main loop
                    # so we need to call update() to refresh the screen immediately - ie to 'animate'
                    self.Update()
                    if i != 0:
                        time.sleep(ptw.easeInQuart(abs((curr_pos - i + 1) / diff)) / int((max_pos - def_pos) * 0.75))
                        print(int((max_pos - def_pos) * 0.75))
                        # TODO don't like sleeping the tween - threading version, maybe use position not time
                        # Also maybe extend function for clicking on a point animation
        #         print(time.perf_counter() - start)
                self.set_position(destination)

    def _parse_limits(self, position, max_pos):
        parsed_position = position
        index = self.index
        if position[index] > max_pos[index]:
            return max_pos
        elif position[index] < 0:
            if self.index:

                return (max_pos[0], 0)
            else:
               return (0, max_pos[1])
        return parsed_position


def rect_centre(size, origin=(0, 0)):
    """
    Returns the centre point of a rectangle

    :param size: wx.Size (width, height)
    :param origin: wx.Point (x,y) Top left co-ordinate
    :return: wx.Point: (x,y)
    """
    origin_x, origin_y = origin
    size_x, size_y = size
    centre_x = (size_x - origin_x) // 2
    centre_y = (size_y - origin_y) // 2
    return wx.Point(centre_x, centre_y)
