import gtk
import gettext

import interface
import os

import common

class wid_picture(interface.widget_interface):
	def __init__(self, window, parent, model, attrs={}):
		interface.widget_interface.__init__(self, window, parent, model, attrs)

		self.widget = gtk.VBox(homogeneous=False)
		self.wid_picture = gtk.Image()
		self.widget.pack_start(self.wid_picture, expand=True, fill=True)

		self.value=False

	def value_set(self, model, model_field):
		self.model_field.set( model, self._value )

	def display(self, model, model_field):
		if not model_field:
			return False
		super(wid_picture, self).display(model_field)
		value = model_field.get(model)
		import base64
		self._value = value
		if self._value:
			value = base64.decodestring(self._value)
			loader = gtk.gdk.PixbufLoader('jpeg')
			loader.write (value, len(value))
			pixbuf = loader.get_pixbuf()
			loader.close()
			self.wid_picture.set_from_pixbuf(pixbuf)
		else:
			self.wid_picture.set_from_pixbuf(None)
