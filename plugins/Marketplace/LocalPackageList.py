# Copyright (c) 2021 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from operator import attrgetter

from PyQt5.QtCore import pyqtSlot, QObject

if TYPE_CHECKING:
    from PyQt5.QtCore import QObject

from UM.i18n import i18nCatalog
from UM.TaskManagement.HttpRequestManager import HttpRequestManager
from UM.Logger import Logger

from .PackageList import PackageList
from .PackageModel import PackageModel
from . import Marketplace

catalog = i18nCatalog("cura")


class LocalPackageList(PackageList):
    PACKAGE_CATEGORIES = {
        "installed":
            {
                "plugin": catalog.i18nc("@label", "Installed Plugins"),
                "material": catalog.i18nc("@label", "Installed Materials")
            },
        "bundled":
            {
                "plugin": catalog.i18nc("@label", "Bundled Plugins"),
                "material": catalog.i18nc("@label", "Bundled Materials")
            }
    }  # The section headers to be used for the different package categories

    def __init__(self, parent: Optional["QObject"] = None) -> None:
        super().__init__(parent)
        self._has_footer = False

    @pyqtSlot()
    def updatePackages(self) -> None:
        """Update the list with local packages, these are materials or plugin, either bundled or user installed. The list
        will also contain **to be removed** or **to be installed** packages since the user might still want to interact
        with these.
        """
        self.setErrorMessage("")  # Clear any previous errors.
        self.setIsLoading(True)

        # Obtain and sort the local packages
        self.setItems([{"package": p} for p in [self._makePackageModel(p) for p in self._manager.locally_installed_packages]])
        self.sort(attrgetter("sectionTitle", "canUpdate", "displayName"), key = "package", reverse = True)
        self.checkForUpdates(self._manager.locally_installed_packages)

        self.setIsLoading(False)
        self.setHasMore(False)  # All packages should have been loaded at this time

    def _makePackageModel(self, package_info: Dict[str, Any]) -> PackageModel:
        """ Create a PackageModel from the package_info and determine its section_title"""
        bundled_or_installed = "installed" if self._manager.isUserInstalledPackage(package_info["package_id"]) else "bundled"
        package_type = package_info["package_type"]
        section_title = self.PACKAGE_CATEGORIES[bundled_or_installed][package_type]
        return PackageModel(package_info, installation_status = bundled_or_installed, section_title = section_title, parent = self)

    def checkForUpdates(self, packages: List[Dict[str, Any]]):
        installed_packages = "installed_packages=".join([f"{package['package_id']}:{package['package_version']}&" for package in packages])
        request_url = f"{Marketplace.PACKAGE_UPDATES_URL}?installed_packages={installed_packages[:-1]}"

        self._ongoing_request = HttpRequestManager.getInstance().get(
            request_url,
            scope = self._scope,
            callback = self._parseResponse
        )

    def _parseResponse(self, reply: "QNetworkReply") -> None:
        """
        Parse the response from the package list API request which can update.

        :param reply: A reply containing information about a number of packages.
        """
        response_data = HttpRequestManager.readJSON(reply)
        if "data" not in response_data:
            Logger.error(
                f"Could not interpret the server's response. Missing 'data' from response data. Keys in response: {response_data.keys()}")
            return
        if len(response_data["data"]) == 0:
            return

        for package_data in response_data["data"]:
            index = self.find("package", package_data["package_id"])
            self.getItem(index)["package"].canUpdate = True

        self.sort(attrgetter("sectionTitle", "canUpdate", "displayName"), key = "package", reverse = True)
