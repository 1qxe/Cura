# Copyright (c) 2021 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from PyQt5.QtCore import pyqtProperty, QObject
import re
from typing import Any, Dict, Optional, Union

from PyQt5.QtCore import pyqtProperty, pyqtSignal, QObject

from UM.i18n import i18nCatalog  # To translate placeholder names if data is not present.
catalog = i18nCatalog("cura")


class PackageModel(QObject):
    """
    Represents a package, containing all the relevant information to be displayed about a package.

    Effectively this behaves like a glorified named tuple, but as a QObject so that its properties can be obtained from
    QML. The model can also be constructed directly from a response received by the API.
    """

    def __init__(self, package_data: Dict[str, Any], section_title: Optional[str] = None, parent: Optional[QObject] = None) -> None:
        """
        Constructs a new model for a single package.
        :param package_data: The data received from the Marketplace API about the package to create.
        :param section_title: If the packages are to be categorized per section provide the section_title
        :param parent: The parent QML object that controls the lifetime of this model (normally a PackageList).
        """
        super().__init__(parent)
        self._package_id = package_data.get("package_id", "UnknownPackageId")
        self._package_type = package_data.get("package_type", "")
        self._is_installed = package_data.get("is_installed", False)
        self._is_active = package_data.get("is_active", False)
        self._is_bundled = package_data.get("is_bundled", False)
        self._icon_url = package_data.get("icon_url", "")
        self._display_name = package_data.get("display_name", catalog.i18nc("@label:property", "Unknown Package"))
        tags = package_data.get("tags", [])
        self._is_checked_by_ultimaker = (self._package_type == "plugin" and "verified" in tags) or (self._package_type == "material" and "certified" in tags)
        self._package_version = package_data.get("package_version", "")  # Display purpose, no need for 'UM.Version'.
        self._package_info_url = package_data.get("website", "")  # Not to be confused with 'download_url'.
        self._download_count = package_data.get("download_count", 0)
        self._description = package_data.get("description", "")
        self._formatted_description = self._format(self._description)

        self._download_url = package_data.get("download_url", "")
        self._release_notes = package_data.get("release_notes", "")  # Not used yet, propose to add to description?

        author_data = package_data.get("author", {})
        self._author_name = author_data.get("display_name", catalog.i18nc("@label:property", "Unknown Author"))
        self._author_info_url = author_data.get("website", "")
        if not self._icon_url or self._icon_url == "":
            self._icon_url = author_data.get("icon_url", "")

        self._can_update = False
        self._section_title = section_title
        # Note that there's a lot more info in the package_data than just these specified here.

    def __eq__(self, other: Union[str, "PackageModel"]):
        if isinstance(other, PackageModel):
            return other._package_id == self._package_id
        else:
            return other == self._package_id

    def __repr__(self):
        return f"<{self._package_id} : {self._package_version} : {self._section_title}>"

    def _format(self, text: str) -> str:
        """
        Formats a user-readable block of text for display.
        :return: A block of rich text with formatting embedded.
        """
        # Turn all in-line hyperlinks into actual links.
        url_regex = re.compile(r"(((http|https)://)[a-zA-Z0-9@:%._+~#?&/=]{2,256}\.[a-z]{2,12}(/[a-zA-Z0-9@:%.-_+~#?&/=]*)?)")
        text = re.sub(url_regex, r'<a href="\1">\1</a>', text)

        return text

    @pyqtProperty(str, constant = True)
    def packageId(self) -> str:
        return self._package_id

    @pyqtProperty(str, constant = True)
    def packageType(self) -> str:
        return self._package_type

    @pyqtProperty(str, constant=True)
    def iconUrl(self):
        return self._icon_url

    @pyqtProperty(str, constant = True)
    def displayName(self) -> str:
        return self._display_name

    @pyqtProperty(bool, constant = True)
    def isCheckedByUltimaker(self):
        return self._is_checked_by_ultimaker

    @pyqtProperty(str, constant=True)
    def packageVersion(self):
        return self._package_version

    @pyqtProperty(str, constant=True)
    def packageInfoUrl(self):
        return self._package_info_url

    @pyqtProperty(int, constant=True)
    def downloadCount(self):
        return self._download_count

    @pyqtProperty(str, constant=True)
    def description(self):
        return self._description

    @pyqtProperty(str, constant = True)
    def formattedDescription(self) -> str:
        return self._formatted_description

    @pyqtProperty(str, constant=True)
    def authorName(self):
        return self._author_name

    @pyqtProperty(str, constant=True)
    def authorInfoUrl(self):
        return self._author_info_url

    @pyqtProperty(str, constant = True)
    def sectionTitle(self) -> Optional[str]:
        return self._section_title

    isInstalledChanged = pyqtSignal()

    @pyqtProperty(bool, notify = isInstalledChanged)
    def isInstalled(self):
        return self._is_installed

    isEnabledChanged = pyqtSignal()

    @pyqtProperty(bool, notify = isEnabledChanged)
    def isEnabled(self):
        return self._is_active

    manageEnableStateChanged = pyqtSignal()

    @pyqtProperty(str, notify = manageEnableStateChanged)
    def manageEnableState(self):
        # TODO: Handle manual installed packages
        if self._is_installed:
            if self._is_active:
                return "secondary"
            else:
                return "primary"
        else:
            return "hidden"

    manageInstallStateChanged = pyqtSignal()

    @pyqtProperty(str, notify = manageInstallStateChanged)
    def manageInstallState(self):
        if self._is_installed:
            if self._is_bundled:
                return "hidden"
            else:
                return "secondary"
        else:
            return "primary"

    manageUpdateStateChanged = pyqtSignal()

    @pyqtProperty(str, notify = manageUpdateStateChanged)
    def manageUpdateState(self):
        if self._can_update:
            return "primary"
        return "hidden"

    @property
    def canUpdate(self):
        return self._can_update

    @canUpdate.setter
    def canUpdate(self, value):
        if value != self._can_update:
            self._can_update = value
            self.manageUpdateStateChanged.emit()
