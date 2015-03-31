from __future__ import unicode_literals
import six

import datetime
from decimal import Decimal
from hashlib import md5
from os.path import join as pjoin
import time
import os

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import formats
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from dbsettings.loading import get_setting_storage, set_setting_value

__all__ = ['Value', 'BooleanValue', 'DecimalValue', 'EmailValue',
           'DurationValue', 'FloatValue', 'IntegerValue', 'PercentValue',
           'PositiveIntegerValue', 'StringValue', 'TextValue', 'PasswordValue',
           'MultiSeparatorValue', 'ImageValue',
           'DateTimeValue', 'DateValue', 'TimeValue']


class Value(object):

    creation_counter = 0
    unitialized_value = None

    def __init__(self, description=None, help_text=None, choices=None, required=True, default=None):
        self.description = description
        self.help_text = help_text
        self.choices = choices or []
        self.required = required
        if default is None:
            self.default = self.unitialized_value
        else:
            self.default = default

        self.creation_counter = Value.creation_counter
        Value.creation_counter += 1

    def __lt__(self, other):
        # This is needed because bisect does not take a comparison function.
        return self.creation_counter < other.creation_counter

    def copy(self):
        new_value = self.__class__()
        new_value.__dict__ = self.__dict__.copy()
        return new_value

    @property
    def key(self):
        return self.module_name, self.class_name, self.attribute_name

    def contribute_to_class(self, cls, attribute_name):
        self.module_name = cls.__module__
        self.class_name = ''
        self.attribute_name = attribute_name
        self.description = self.description or attribute_name.replace('_', ' ')

        setattr(cls, self.attribute_name, self)

    @property
    def app(self):
        return getattr(self, '_app', self.module_name.split('.')[-2])

    def __get__(self, instance=None, cls=None):
        if instance is None:
            raise AttributeError("%r is only accessible from %s instances." %
                                 (self.attribute_name, cls.__name__))
        try:
            storage = get_setting_storage(*self.key)

            # Depending on the setting type, we pass that specific database value to generate a python object       
            if isinstance(self, ImageValue):
                return self.to_python(storage.value_image)                
            else:
                return self.to_python(storage.value)
        except:
            return None

    def __set__(self, instance, value):
        current_value = self.__get__(instance)
        if self.to_python(value) != current_value:
            set_setting_value(*(self.key + (value,)))

    # Subclasses should override the following methods where applicable

    def to_python(self, value):
        "Returns a native Python object suitable for immediate use"
        return value

    def get_db_prep_save(self, value):
        "Returns a value suitable for storage into a CharField"
        return six.text_type(value)

    def to_editor(self, value):
        "Returns a value suitable for display in a form widget"
        return six.text_type(value)

###############
# VALUE TYPES #
###############


class BooleanValue(Value):
    unitialized_value = False

    class field(forms.BooleanField):

        def __init__(self, *args, **kwargs):
            kwargs['required'] = False
            forms.BooleanField.__init__(self, *args, **kwargs)

    def to_python(self, value):
        if value in (True, 't', 'True'):
            return True
        return False

    to_editor = to_python


class DecimalValue(Value):
    field = forms.DecimalField

    def to_python(self, value):
        return Decimal(value)


# DurationValue has a lot of duplication and ugliness because of issue #2443
# Until DurationField is sorted out, this has to do some extra work
class DurationValue(Value):

    class field(forms.CharField):
        def clean(self, value):
            try:
                return datetime.timedelta(seconds=float(value))
            except (ValueError, TypeError):
                raise forms.ValidationError('This value must be a real number.')
            except OverflowError:
                raise forms.ValidationError('The maximum allowed value is %s' %
                                            datetime.timedelta.max)

    def to_python(self, value):
        if isinstance(value, datetime.timedelta):
            return value
        try:
            return datetime.timedelta(seconds=float(value))
        except (ValueError, TypeError):
            raise forms.ValidationError('This value must be a real number.')
        except OverflowError:
            raise forms.ValidationError('The maximum allowed value is %s' % datetime.timedelta.max)

    def get_db_prep_save(self, value):
        return six.text_type(value.days * 24 * 3600 + value.seconds
                             + float(value.microseconds) / 1000000)


class FloatValue(Value):
    field = forms.FloatField

    def to_python(self, value):
        return float(value)


class IntegerValue(Value):
    field = forms.IntegerField

    def to_python(self, value):
        return int(value)


class PercentValue(Value):

    class field(forms.DecimalField):

        def __init__(self, *args, **kwargs):
            forms.DecimalField.__init__(self, 100, 0, 5, 2, *args, **kwargs)

        class widget(forms.TextInput):
            def render(self, *args, **kwargs):
                # Place a percent sign after a smaller text field
                attrs = kwargs.pop('attrs', {})
                attrs['size'] = attrs['max_length'] = 6
                return forms.TextInput.render(self, attrs=attrs, *args, **kwargs) + '%'

    def to_python(self, value):
        return Decimal(value) / 100


class PositiveIntegerValue(IntegerValue):

    class field(forms.IntegerField):

        def __init__(self, *args, **kwargs):
            kwargs['min_value'] = 0
            forms.IntegerField.__init__(self, *args, **kwargs)


class StringValue(Value):
    unitialized_value = ''
    field = forms.CharField


class TextValue(Value):
    unitialized_value = ''
    class field(forms.CharField):
        widget = forms.Textarea

    def to_python(self, value):
        return six.text_type(value)

class EmailValue(Value):
    unitialized_value = ''
    field = forms.EmailField

    def to_python(self, value):
        return six.text_type(value)


class PasswordValue(Value):
    class field(forms.CharField):
        widget = forms.PasswordInput

        def __init__(self, **kwargs):
            if not kwargs.get('help_text'):
                kwargs['help_text'] = _(
                    'Leave empty in order to retain old password. Provide new value to change.')
            forms.CharField.__init__(self, **kwargs)

        def clean(self, value):
            # Retain old password if not changed
            if value == '':
                value = self.initial
            return forms.CharField.clean(self, value)


class MultiSeparatorValue(TextValue):
    """Provides a way to store list-like string settings.
    e.g 'mail@test.com;*@blah.com' would be returned as
        ['mail@test.com', '*@blah.com']. What the method
        uses to split on can be defined by passing in a
        separator string (default is semi-colon as above).
    """

    def __init__(self, description=None, help_text=None, separator=';', required=True,
                 default=None):
        self.separator = separator
        if default is not None:
            # convert from list to string
            default = separator.join(default)
        super(MultiSeparatorValue, self).__init__(description=description,
                                                  help_text=help_text,
                                                  required=required,
                                                  default=default)

    class field(forms.CharField):

        class widget(forms.Textarea):
            pass

    def to_python(self, value):
        if value:
            value = six.text_type(value)
            value = value.split(self.separator)
            value = [x.strip() for x in value]
        else:
            value = []
        return value


class ImageValue(Value):
    def __init__(self, *args, **kwargs):
        if 'upload_to' in kwargs:
            self._upload_to = kwargs.pop('upload_to', '')
        super(ImageValue, self).__init__(*args, **kwargs)

    class field(forms.ImageField):
        class widget(forms.FileInput):
            "Widget with preview"

            def render(self, name, value, attrs=None):
                output = []

                try:
                    if not value:
                        raise IOError('No value')

                    from PIL import Image
                    Image.open(value.file)
                    file_name = pjoin(settings.MEDIA_URL, value.name).replace("\\", "/")
                    params = {"file_name": file_name}
                    output.append('<p><img src="%(file_name)s" width="100" /></p>' % params)
                except IOError:
                    pass

                output.append(forms.FileInput.render(self, name, value, attrs))
                return mark_safe(''.join(output))

    def to_python(self, value):
        # Return the value which is an ImageField image
        return value

    def get_db_prep_save(self, value):
        # Return the value which is an ImageField image
        return value

    def to_editor(self, value):
        "Returns a value suitable for display in a form widget"
        if not value:
            return None
        return value

class DateTimeValue(Value):
    field = forms.DateTimeField
    formats_source = 'DATETIME_INPUT_FORMATS'

    @property
    def _formats(self):
        return formats.get_format(self.formats_source)

    def _parse_format(self, value):
        for format in self._formats:
            try:
                return datetime.datetime.strptime(value, format)
            except (ValueError, TypeError):
                continue
        return None

    def get_db_prep_save(self, value):
        if isinstance(value, six.string_types):
            return value
        return value.strftime(self._formats[0])

    def to_python(self, value):
        if isinstance(value, datetime.datetime):
            return value
        return self._parse_format(value)


class DateValue(DateTimeValue):
    field = forms.DateField
    formats_source = 'DATE_INPUT_FORMATS'

    def to_python(self, value):
        if isinstance(value, datetime.datetime):
            return value.date()
        elif isinstance(value, datetime.date):
            return value
        res = self._parse_format(value)
        if res is not None:
            return res.date()
        return res


class TimeValue(DateTimeValue):
    field = forms.TimeField
    formats_source = 'TIME_INPUT_FORMATS'

    def to_python(self, value):
        if isinstance(value, datetime.datetime):
            return value.time()
        elif isinstance(value, datetime.time):
            return value
        res = self._parse_format(value)
        if res is not None:
            return res.time()
        return res
