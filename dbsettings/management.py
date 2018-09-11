from django.db.models.signals import post_migrate


def mk_permissions(permissions, appname, verbosity):
    """
    Make permission at app level - hack with empty ContentType.

    Adapted code from http://djangosnippets.org/snippets/334/
    """
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    # create a content type for the app
    ct, created = ContentType.objects.get_or_create(model='', app_label=appname,
                                                    defaults={'name': appname})
    if created and verbosity >= 2:
        print("Adding custom content type '%s'" % ct)
    # create permissions
    for codename, name in permissions:
        p, created = Permission.objects.get_or_create(codename=codename,
                                                      content_type__pk=ct.id,
                                                      defaults={'name': name, 'content_type': ct})
        if created and verbosity >= 2:
            print("Adding custom permission '%s'" % p)


def handler(sender, **kwargs):
    from dbsettings.loading import get_app_settings
    app_label = sender.label
    are_global_settings = any(not s.class_name for s in get_app_settings(app_label))
    if are_global_settings:
        permission = (
            'can_edit__settings',
            'Can edit %s non-model settings' % app_label,
        )

        # Disable the making of perms based on the app settings app,
        # instead we will just use the global dbsettings perm, as there
        # are issues with app level perms, for instance apps without
        # model migrations won't work, and migrate keeps complaining
        # to delete stale content types...
        
        # mk_permissions([permission], app_label, 0)


post_migrate.connect(handler)
