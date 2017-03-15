from collections import OrderedDict
from django.core.cache import cache
from dbsettings.models import Setting
from django.conf import settings
import dbsettings

__all__ = ['get_all_settings', 'get_setting', 'get_setting_storage',
           'register_setting', 'unregister_setting', 'set_setting_value']


_settings = OrderedDict()


def _get_cache_key(module_name, class_name, attribute_name):
    return '.'.join(['dbsettings', settings.APP_ENTRY['id'], module_name, class_name, attribute_name])


def get_all_settings():
    return list(_settings.values())


def get_app_settings(app_label):
    return [p for p in _settings.values() if app_label == p.app]


def get_setting(module_name, class_name, attribute_name):
    return _settings[module_name, class_name, attribute_name]


def setting_in_db(module_name, class_name, attribute_name):
    return Setting.objects.filter(
        module_name=module_name,
        class_name=class_name,
        attribute_name=attribute_name,
    ).count() == 1


def get_setting_storage(module_name, class_name, attribute_name):
    key = _get_cache_key(module_name, class_name, attribute_name)
    storage = cache.get(key)
    if storage is None:
        try:
            storage = Setting.objects.get(
                module_name=module_name,
                class_name=class_name,
                attribute_name=attribute_name,
            )
        except Setting.DoesNotExist:
            setting_object = get_setting(module_name, class_name, attribute_name)

            # TODO Add back support for defaults
            storage = Setting(
                module_name=module_name,
                class_name=class_name,
                attribute_name=attribute_name,
                #value=setting_object.default,
            )
        cache.set(key, storage)
    return storage


def register_setting(setting):
    if setting.key not in _settings:
        _settings[setting.key] = setting


def unregister_setting(setting):
    if setting.key in _settings and _settings[setting.key] is setting:
        del _settings[setting.key]


def set_setting_value(module_name, class_name, attribute_name, value):

    setting = get_setting(module_name, class_name, attribute_name)
    storage = get_setting_storage(module_name, class_name, attribute_name)

    if isinstance(setting, dbsettings.values.ImageValue):
        # Save to the image field so contains width and height properties as well
        image = setting.get_db_prep_save(value)
        storage.value_image.save(image.name, image)
    else:
        # Everything else store as text
        storage.value_text = setting.get_db_prep_save(value)

    storage.save()
    key = _get_cache_key(module_name, class_name, attribute_name)
    cache.delete(key)
