from setuptools import setup, find_packages

# Dynamically calculate the version based on dbsettings.VERSION
version_tuple = (0, 7, None)
if version_tuple[2] is not None:
    if type(version_tuple[2]) == int:
        version = "%d.%d.%s" % version_tuple
    else:
        version = "%d.%d_%s" % version_tuple
else:
    version = "%d.%d" % version_tuple[:2]

setup(
    name='django-dbsettings',
    version="0.7.2-post4",
    description='Application settings whose values can be updated while a project is up and running.',
    long_description=open('README.rst').read(),
    author='Samuel Cormier-Iijima',
    author_email='sciyoshi@gmail.com',
    maintainer='Jacek Tomaszewski',
    maintainer_email='jacek.tomek@gmail.com',
    url='http://github.com/zlorf/django-dbsettings',
    packages=find_packages(),
    include_package_data=True,
    license='BSD',
    install_requires=(
    ),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities'
    ],
    zip_safe=False,    
)
