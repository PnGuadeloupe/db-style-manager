from os.path import dirname, abspath, join
from qgis.PyQt.QtCore import QCoreApplication


def tr(message):
    """Get the translation for a string using Qt translation API.

    We implement this ourselves since we do not inherit QObject.

    :param message: String for translation.
    :type message: str, QString

    :returns: Translated version of message.
    :rtype: QString
    """
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    return QCoreApplication.translate('DbStyleManager', message)


def resources_path(*args):
    """Get the path to our resources folder.
    .. versionadded:: 1.5.3
    Note that in version 1.5.3 we removed the use of Qt Resource files in
    favour of directly accessing on-disk resources.
    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str
    :return: Absolute path to the resources folder.
    :rtype: str
    """
    path = dirname(__file__)
    path = abspath(join(path, 'resources'))
    for item in args:
        path = abspath(join(path, item))

    return path
