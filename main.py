import shutil
from builtins import dir
from datetime import datetime
from io import BytesIO
from tempfile import mkdtemp

import math
import os
from random import sample
from PIL import Image as PilImage

from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty
from kivy.uix.button import Button, ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, SwapTransition
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader


# mv ~/AlBumdoTrash/* ~/kivy/AlBumdo/photos/


class MouseOver(Widget):

    def __init__(self, **kwargs):
        Window.bind(mouse_pos=self._mouse_move)
        self.hovering = BooleanProperty(False)
        self.poi = ObjectProperty(None)
        self.register_event_type('on_hover')
        self.register_event_type('on_exit')
        super(MouseOver, self).__init__(**kwargs)

    def _mouse_move(self, *args):
        if not self.get_root_window():
            return
        is_collide = self.collide_point(*self.to_widget(*args[1]))
        if self.hovering == is_collide:
            return
        self.poi = args[1]
        self.hovering = is_collide
        self.dispatch('on_hover' if is_collide else 'on_exit')

    def on_hover(self):
        """Mouse over"""

    def on_exit(self):
        """Mouse leaves"""


class NextPrevSelector(Button, MouseOver):
    """ Base class for Prev and Next Image Buttons"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.width = 100
        self.hpos = 99
        self.pos = (0, self.hpos)
        self.opacity = 0

    def on_hover(self):
        self.opacity = .1

    def on_exit(self):
        self.opacity = 0

    def on_press(self):
        self.parent.image.next_image()


class Photos:

    def __init__(self, source):
        self.path = source
        self.img_data = []
        self._load_photos()
        self.n_img = len(self.img_data)
        self.del_dir = os.path.join(os.path.expanduser('~'), 'AlBumdoTrash')
        os.makedirs(self.del_dir, exist_ok=True)
        self.pos = 0

    def _load_photos(self):
        listOfFiles = self.list_image_files(self.path, with_dir=True)
        for d, x in listOfFiles:
            try:
                created_time = os.path.getctime(x)
            except OSError:
                created_time = 0
            date = {'image': x, 'created': created_time, 'dir': d}
            self.img_data.append(date)
        self.img_data.sort(key=lambda x: x['created'], reverse=True)

    @staticmethod
    def list_image_files(path, with_dir=False):
        listOfFiles = list()
        for (dirpath, dirnames, filenames) in os.walk(path):
            listOfFiles += [
                (dirpath, os.path.join(dirpath, file)) for file in filenames
                if file.lower().endswith(
                    ('.jpeg', '.jpg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.ico', \
                     '.mng', '.tga', '.psd', '.xcf', '.svg', '.icns')
                )]
        if with_dir:
            return listOfFiles
        else:
            return [i[1] for i in listOfFiles]

    def list_images(self):
        return [img['image'] for img in self.img_data]


class PreviewBar(BoxLayout):
    """ Dynamic amount of preview images that can be selected"""

    def __init__(self, meta=None, **kwargs):
        self.meta = meta
        super().__init__(**kwargs)
        self.height = 100
        self.size_hint = (1, None)
        self.pos = (0, 0)
        self.images = 10
        self.update()

    def update(self):
        self.clear_widgets()
        n = len(self.meta.img_data)
        for i in range(self.images):
            if n>1:
                image_pos = self.meta.pos + i - int(math.floor(self.images/2))
                #image_pos vary (-5, n+4)
                correction = 2 if n == 2 else 1
                if image_pos < 0:
                    image_pos += n*correction
                if image_pos >= n:
                    image_pos -= n*correction

                img = MenuImage(source=self.meta.img_data[image_pos]['image'],
                                image_pos=image_pos,
                                selected=True if image_pos == self.meta.pos else False)
                self.add_widget(img)


    def size_change(self, width=1920):
        self.images = int(width / 100)
        if self.images < 1:
            self.images = 1
        self.update()


class MenuImage(ButtonBehavior, Image, MouseOver):
    """ Preview image. The current one will always have full opacity,
        otherwise only ones being hovered over will be full opacity. """

    def __init__(self, image_pos=0, selected=False, **kwargs):
        self.image_pos = image_pos
        self.selected = selected
        self.alpha = .4
        super().__init__(**kwargs)
        self.width = 100
        if not self.selected:
            self.opacity = self.alpha
        else:
            self.opacity = 0.9
        self.size_hint = None, None

    def on_press(self):
        if not self.selected:
            self.parent.parent.change_to_image(self.image_pos)

    def on_hover(self):
        if not self.selected:
            self.opacity = .8

    def on_exit(self):
        if not self.selected:
            self.opacity = self.alpha


class MainImage(Image):

    def __init__(self, meta=None, preview_bar=None, **kwargs):
        self.meta = meta
        self.preview_bar = preview_bar
        super().__init__(source=self.get('image'), **kwargs)
        self.pos = (0, 100)
        self.size_hint_x = 1
        self.size_hint_y = .8

    def set_pos(self):
        if self.meta.pos >= len(self.meta.img_data):
            return 0
        else:
            return self.meta.pos

    def get(self, key):
        return self.meta.img_data[self.set_pos()][key]

    def get_score(self):
        #TODO Score class?
        fn = self.get('image')
        fn = ''.join(fn.split('/'))

        score = 0
        for dirpath, dirnames, filenames in os.walk('scores/', followlinks=True):
            if fn in filenames:
                score = dirpath.split('/')[-1]
        return int(score)

    def next_image(self):
        self.meta.pos += 1
        if self.meta.pos >= len(self.meta.img_data):
            self.meta.pos = 0
        self.update()

    def prev_image(self):
        self.meta.pos -= 1
        if self.meta.pos < 0:
            self.meta.pos = len(self.meta.img_data) - 1
        self.update()

    def update(self):
        self.source = self.get('image')
        self.reload()
        self.preview_bar.update()
        self.parent.children[0].children[0].text = '*'*self.get_score()


class ScoreButton(Button):

    def __init__(self, score, img, **kwargs):
        super().__init__(**kwargs)
        self.score = str(score)
        self.text = '*'*score
        self.image = img
        self.score_path = 'scores'
        score_dir = os.path.join(self.score_path, self.score)
        if not os.path.exists(score_dir):
            os.mkdir(score_dir)

    def on_release(self):
        img_path = self.image.get('image')
        fn = ''.join(img_path.split('/'))
        for s in os.listdir(self.score_path):
            old_score = os.path.join(self.score_path, s, fn)
            if os.path.exists(old_score):
                os.remove(old_score)
        os.symlink(src=img_path, dst=os.path.join(self.score_path, self.score, fn))
        self.image.next_image()



class Options(BoxLayout):

    def __init__(self, img, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(ScoreButton(score=1, img=img))
        self.add_widget(ScoreButton(score=2, img=img))
        self.add_widget(ScoreButton(score=3, img=img))
        self.add_widget(Button(text='*'*img.get_score()))
        self.size_hint_y = .04
        # self.height = 35
        self.pos_hint = {'top': 1}


class ImageViewer(FloatLayout):

    def __init__(self, path, **kwargs):
        super().__init__(**kwargs)
        # Capture keyboard input
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self.pos = (0, 0)
        self.size_hint = (1, 1)

        self.photos = Photos(source=path)
        self.preview = PreviewBar(meta=self.photos)
        self.image = MainImage(meta=self.photos, preview_bar=self.preview)
        self.options = Options(img=self.image)
        self.next_button = NextPrevSelector(text=">")
        self.prev_button = NextPrevSelector(text="<")

        self.add_widget(self.options, index=0)
        self.add_widget(self.image, index=3)
        self.add_widget(self.preview, index=1)
        self.add_widget(self.next_button, index=2)
        self.add_widget(self.prev_button, index=2)

    def on_size(self, obj, size):
        """Make sure all children sizes adjust properly"""
        # log.debug(f"Resizing image window to {size[0]}x{size[1]}")
        self.next_button.pos = (self.width - 99, self.next_button.hpos)
        self.preview.size_change(width=size[0])
        self.image.height = self.height - 100
        self.next_button.size_hint_y = .9
        self.next_button.height = self.height - 100
        self.prev_button.height = self.height - 100

    def delete_image(self):
        img = self.photos.img_data[self.photos.pos]
        self.photos.img_data.remove(img)
        del_name = (f"{datetime.now().isoformat().replace(':', '.')}"
                    f"-_-{img['image'].split('/')[-1]}")
        shutil.move(img['image'],
                    os.path.join(self.photos.del_dir, del_name))

        #clear score -> TODO to class Score
        for r, d, f in os.walk('scores'):
            for file in f:
                if ''.join(img['image']) == file:
                    os.unlink(os.path.join(r, file))

        self.change_to_image(self.photos.pos)

    def change_to_image(self, image_pos):
        self.photos.pos = image_pos
        self.image.source = self.image.meta.img_data[self.image.set_pos()]['image']
        self.image.reload()
        self.preview.update()

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'right':
            self.image.next_image()
        elif keycode[1] == 'left':
            self.image.prev_image()
        elif keycode[1] == 'delete':
            self.delete_image()
        elif keycode[1] == 'backspace':
            if not self.parent.parent.current == 'Menu':
                self.parent.parent.current = 'Menu'
                self.parent.parent.screens[0].clear_widgets()
                self.parent.parent.screens[0].add_widget(MenuWindow(path='/home/lima/kivy/AlBumdo/photos'))
        return True


class ImageButton(ButtonBehavior, Image):
    def __init__(self, path, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.keep_ratio = False
        self.allow_stretch = True
        self.photos_paths = Photos.list_image_files(path=path)
        ## TODO: przeredagować nie arg directory, tylko zagnieżdżenie w Photos(): czy po "dir+path" czy po "score"
        with self.canvas:
            Color(0, 0, 0, .35)
            self.rect = Rectangle(pos=(0, 0))
            path = '/'.join(path.split('/')[-2:])
            n = len(self.photos_paths)
            self.lab = Label(text='%s/\n%i' % (path, n))
        self.bind(pos=self.update_shape, size=self.update_shape)
        self.cover()

    def update_shape(self, *args):
        self.rect.pos = self.pos
        self.rect.size = (self.size[0], Window.size[1]/12)
        self.lab.pos = (self.pos[0]+10, self.pos[1]-30)
        self.lab.pos_hint = (None, None)

    def on_release(self):
        self.parent.parent.parent.parent.parent.screens[1].clear_widgets()
        self.parent.parent.parent.parent.parent.screens[1].add_widget(ImageViewer(path=self.path))
        self.parent.parent.parent.parent.parent.current = 'Viewer'

    def cover(self):
        p = self.path
        if any([os.path.isdir(os.path.join(p, x)) for x in os.listdir(p)]):
            mini_covers = sample(self.photos_paths, min(4, len(self.photos_paths)))

            file = BytesIO()
            w, h = self.size
            new_cover = PilImage.new('RGB', size=(int(w), int(h)))
            x, y = int(w/2), int(h/2)
            for elem, (i,j) in zip(mini_covers, ((0,0), (0,1), (1,0), (1,1))):
                im = PilImage.open(elem)
                im.crop(self.crop_img((x,y)))
                new_cover.paste(im, (i*x, j*y))
            new_cover.save(file, 'png')
            file.seek(0)
            fileData = BytesIO(file.read())
            self.texture = CoreImage(fileData, ext='png').texture
        else:
            if len(self.photos_paths):
                self.source = self.photos_paths[0]
                self.set_region()

    def crop_img(self, size):
        W, H = self.size # Window size related
        w, h = size
        if (W<w) and (H<h):
            new_w, new_h = W, H
        elif (W>w) and (H>h):
            new_w, new_h = w, w*H/W
        else:
            if h>w:
                new_w, new_h = W, h
            else:
                new_w, new_h = w, H
        offset_x, offset_y = int(abs(w-new_w)/2), int(abs(h-new_h)/2)
        return offset_x, offset_y, offset_x+new_w, offset_y+new_h

    def set_region(self):
        self.texture = self.texture.get_region(*self.crop_img(self.texture_size))


class Tiles(GridLayout):

    def __init__(self, path, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2 #if Window.size[0] < Window.size[1] else 3
        self.spacing = 6.28
        images_paths = Photos.list_image_files(path=path)
        self.pics_dirs = set([os.path.dirname(i) for i in images_paths])

        ## TODO: others catalog
        # self.others = [name for name in os.listdir(photos_path) if not os.path.isdir(os.path.join(photos_path, name))]
        ### add ALL
        self.rows = 1 + len(self.pics_dirs)
        self.img_size = Window.size[0]/self.cols, Window.size[1]/math.ceil(self.rows/self.cols)
        self.add_widget(ImageButton(path=path, size=self.img_size))
        for p in self.pics_dirs:
            self.add_widget(ImageButton(
                path=p,
                size=self.img_size
            ))
        # self.add_widget(ImageButton(directory))
        # otherpath = mkdtemp()
        # [os.system('cp %s %s' % (f, otherpath)) for f in self.others]
        # self.add_widget(ImageButton(directory=otherpath, size=self.img_size))


class MenuWindow(TabbedPanel): #(Float...)

    def __init__(self, path, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.do_default_tab = False
        self.th_dir = TabbedPanelHeader(text='Directories')
        self.th_dir.content = Tiles(path=path)
        self.th_cat = TabbedPanelHeader(text='Ratings')
        self.th_cat.content = Tiles(path='/home/lima/kivy/AlBumdo/scores')
        self.add_widget(self.th_dir)
        self.add_widget(self.th_cat)
        self.set_def_tab(self.th_dir)

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] in ['left', 'backspace', 'right']:
            self.switch_to([i for i in self.tab_list if not i==self.current_tab][0])
        return True


class AlBumdoApp(App):

    def build(self):
        self.path = '/home/lima/kivy/AlBumdo/photos'
        self.sm = sm = ScreenManager(transition=SwapTransition())
        sm.add_widget(Screen(name='Menu'))
        sm.add_widget(Screen(name='Viewer'))
        sm.screens[0].add_widget(MenuWindow(path=self.path))

        return self.sm


if __name__ == '__main__':
    AlBumdoApp().run()
