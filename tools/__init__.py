import Qt

if not hasattr(Qt.QtCompat, "isValid"):

    if Qt.IsPyQt4 or Qt.IsPyQt5:
        Qt.QtCompat.isValid = lambda x: not getattr(Qt, "_sip").isdeleted(x)
    elif Qt.IsPySide2:
        Qt.QtCompat.isValid = getattr(Qt, "_shiboken2").isValid
    elif Qt.IsPySide:
        Qt.QtCompat.isValid = getattr(Qt, "_shiboken").isValid
    else:
        raise AttributeError("'module' has no attribute 'isValid'")
