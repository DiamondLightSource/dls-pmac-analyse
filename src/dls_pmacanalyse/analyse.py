import logging
import os
from datetime import datetime
from typing import cast
from xml.dom.minidom import getDOMImplementation

from dls_pmacanalyse.errors import ConfigError, PmacReadError
from dls_pmacanalyse.globalconfig import GlobalConfig
from dls_pmacanalyse.pmacstate import PmacState
from dls_pmacanalyse.pmacvariables import PmacMVariable
from dls_pmacanalyse.webpage import WebPage

log = logging.getLogger(__name__)


class Analyse:
    def __init__(self, config: GlobalConfig):
        """Constructor."""
        self.config = config
        self.pmacFactorySettings = PmacState("pmacFactorySettings")
        self.geobrickFactorySettings = PmacState("geobrickFactorySettings")

    def analyse(self):
        """Performs the analysis of the PMACs."""
        # Load the factory settings
        factorySettingsFilename = os.path.join(
            os.path.dirname(__file__), "factorySettings_pmac.pmc"
        )
        self.loadFactorySettings(
            self.pmacFactorySettings, factorySettingsFilename, self.config.includePaths
        )
        factorySettingsFilename = os.path.join(
            os.path.dirname(__file__), "factorySettings_geobrick.pmc"
        )
        self.loadFactorySettings(
            self.geobrickFactorySettings,
            factorySettingsFilename,
            self.config.includePaths,
        )
        # Make sure the results directory exists
        if self.config.writeAnalysis:
            if not os.path.exists(self.config.resultsDir):
                os.makedirs(self.config.resultsDir)
            elif not os.path.isdir(self.config.resultsDir):
                raise ConfigError(
                    f"Results path exists but is not a directory: {self.config.resultsDir}"
                )
        # Make sure the backup directory exists if it is required
        if self.config.backupDir is not None:
            if not os.path.exists(self.config.backupDir):
                os.makedirs(self.config.backupDir)
            elif not os.path.isdir(self.config.backupDir):
                raise ConfigError(
                    f"Backup path exists but is not a directory: {self.config.backupDir}"
                )
        if self.config.writeAnalysis is True:
            # Drop a style sheet
            wFile = open(f"{self.config.resultsDir}/analysis.css", "w+")
            wFile.write(
                """
                p{text-align:left; color:black; font-family:arial}
                h1{text-align:center; color:green}
                table{border-collapse:collapse}
                table, th, td{border:1px solid black}
                th, td{padding:5px; vertical-align:top}
                th{background-color:#EAf2D3; color:black}
                em{color:red; font-style:normal; font-weight:bold}
                #code{white-space:pre}
                #code{font-family:courier}
                """
            )
        # Analyse each pmac
        for name, pmac in self.config.pmacs.items():
            if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                # Create the comparison web page
                page = WebPage(
                    "Comparison results for {} ({})".format(
                        pmac.name, datetime.today().strftime("%x %X")
                    ),
                    f"{self.config.resultsDir}/{pmac.name}_compare.htm",
                    styleSheet="analysis.css",
                )
                # Read the hardware (or compare with file)
                if pmac.compareWith is None:
                    try:
                        pmac.readHardware(
                            self.config.backupDir,
                            self.config.checkPositions,
                            self.config.debug,
                            self.config.comments,
                            self.config.verbose,
                        )
                    except PmacReadError:
                        msg = "FAILED TO CONNECT TO " + pmac.name
                        log.debug(msg, exc_info=True)
                        log.error(msg)
                else:
                    pmac.loadCompareWith()
                # Load the reference
                factoryDefs = None
                if pmac.useFactoryDefs:
                    if pmac.geobrick:
                        factoryDefs = self.geobrickFactorySettings
                    else:
                        factoryDefs = self.pmacFactorySettings
                pmac.loadReference(factoryDefs, self.config.includePaths)
                # Make the comparison
                theFixFile = None
                if self.config.fixfile is not None:
                    theFixFile = open(self.config.fixfile, "w")
                theUnfixFile = None
                if self.config.unfixfile is not None:
                    theUnfixFile = open(self.config.unfixfile, "w")
                matches = pmac.compare(page, theFixFile, theUnfixFile)
                if theFixFile is not None:
                    theFixFile.close()
                if theUnfixFile is not None:
                    theUnfixFile.close()
                # Write out the HTML
                if matches:
                    # delete any existing comparison file
                    if os.path.exists(
                        f"{self.config.resultsDir}/{pmac.name}_compare.htm"
                    ):
                        os.remove(f"{self.config.resultsDir}/{pmac.name}_compare.htm")
                else:
                    if self.config.writeAnalysis is True:
                        page.write()
        if self.config.writeAnalysis is True:
            # Create the top level page
            indexPage = WebPage(
                "PMAC analysis ({})".format(datetime.today().strftime("%x %X")),
                f"{self.config.resultsDir}/index.htm",
                styleSheet="analysis.css",
            )
            table = indexPage.table(indexPage.body())
            for _, pmac in self.config.pmacs.items():
                row = indexPage.tableRow(table)
                indexPage.tableColumn(row, f"{pmac.name}")
                if os.path.exists(f"{self.config.resultsDir}/{pmac.name}_compare.htm"):
                    indexPage.href(
                        indexPage.tableColumn(row),
                        f"{pmac.name}_compare.htm",
                        "Comparison results",
                    )
                elif os.path.exists(f"{self.config.resultsDir}/{pmac.name}_plcs.htm"):
                    indexPage.tableColumn(row, "Matches")
                else:
                    indexPage.tableColumn(row, "No results")
                indexPage.href(
                    indexPage.tableColumn(row),
                    f"{pmac.name}_ivariables.htm",
                    "I variables",
                )
                indexPage.href(
                    indexPage.tableColumn(row),
                    f"{pmac.name}_pvariables.htm",
                    "P variables",
                )
                indexPage.href(
                    indexPage.tableColumn(row),
                    f"{pmac.name}_mvariables.htm",
                    "M variables",
                )
                indexPage.href(
                    indexPage.tableColumn(row),
                    f"{pmac.name}_mvariablevalues.htm",
                    "M variable values",
                )
                if pmac.numMacroStationIcs == 0:
                    indexPage.tableColumn(row, "-")
                elif pmac.numMacroStationIcs is None and not os.path.exists(
                    f"{self.config.resultsDir}/{pmac.name}_msivariables.htm"
                ):
                    indexPage.tableColumn(row, "-")
                else:
                    indexPage.href(
                        indexPage.tableColumn(row),
                        f"{pmac.name}_msivariables.htm",
                        "MS variables",
                    )
                indexPage.href(
                    indexPage.tableColumn(row),
                    f"{pmac.name}_coordsystems.htm",
                    "Coordinate systems",
                )
                indexPage.href(
                    indexPage.tableColumn(row), f"{pmac.name}_plcs.htm", "PLCs"
                )
                indexPage.href(
                    indexPage.tableColumn(row),
                    f"{pmac.name}_motionprogs.htm",
                    "Motion programs",
                )
            indexPage.write()
            # Dump the I variables for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    # Create the I variables top level web page
                    page = WebPage(
                        "I Variables for {} ({})".format(
                            pmac.name, datetime.today().strftime("%x %X")
                        ),
                        f"{self.config.resultsDir}/{pmac.name}_ivariables.htm",
                        styleSheet="analysis.css",
                    )
                    page.href(
                        page.body(),
                        f"{pmac.name}_ivars_glob.htm",
                        "Global I variables",
                    )
                    page.lineBreak(page.body())
                    for motor in range(1, pmac.numAxes + 1):
                        page.href(
                            page.body(),
                            f"{pmac.name}_ivars_motor{motor}.htm",
                            f"Motor {motor} I variables",
                        )
                        page.lineBreak(page.body())
                    page.write()
                    # Create the global I variables page
                    page = WebPage(
                        f"Global I Variables for {pmac.name}",
                        f"{self.config.resultsDir}/{pmac.name}_ivars_glob.htm",
                        styleSheet="analysis.css",
                    )
                    pmac.htmlGlobalIVariables(page)
                    page.write()
                    # Create each I variables page
                    for motor in range(1, pmac.numAxes + 1):
                        page = WebPage(
                            f"Motor {motor} I Variables for {pmac.name}",
                            f"{self.config.resultsDir}/{pmac.name}_ivars_motor{motor}.htm",
                            styleSheet="analysis.css",
                        )
                        pmac.htmlMotorIVariables(motor, page)
                        page.write()
            # Dump the macrostation I variables for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    if pmac.numMacroStationIcs > 0:
                        # Create the MS,I variables top level web page
                        page = WebPage(
                            "Macrostation I Variables for {} ({})".format(
                                pmac.name, datetime.today().strftime("%x %X")
                            ),
                            f"{self.config.resultsDir}/{pmac.name}_msivariables.htm",
                            styleSheet="analysis.css",
                        )
                        page.href(
                            page.body(),
                            f"{pmac.name}_msivars_glob.htm",
                            "Global macrostation I variables",
                        )
                        page.lineBreak(page.body())
                        for motor in range(1, pmac.numAxes + 1):
                            page.href(
                                page.body(),
                                f"{pmac.name}_msivars_motor{motor}.htm",
                                f"Motor {motor} macrostation I variables",
                            )
                            page.lineBreak(page.body())
                        page.write()
                        # Create the global macrostation I variables page
                        page = WebPage(
                            f"Global Macrostation I Variables for {pmac.name}",
                            f"{self.config.resultsDir}/{pmac.name}_msivars_glob.htm",
                            styleSheet="analysis.css",
                        )
                        pmac.htmlGlobalMsIVariables(page)
                        page.write()
                        # Create each motor macrostation I variables page
                        for motor in range(1, pmac.numAxes + 1):
                            page = WebPage(
                                f"Motor {motor} Macrostation I Variables for {pmac.name}",
                                f"{self.config.resultsDir}/{pmac.name}_msivars_motor{motor}.htm",
                                styleSheet="analysis.css",
                            )
                            pmac.htmlMotorMsIVariables(motor, page)
                            page.write()
            # Dump the M variables for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    page = WebPage(
                        "M Variables for {} ({})".format(
                            pmac.name, datetime.today().strftime("%x %X")
                        ),
                        f"{self.config.resultsDir}/{pmac.name}_mvariables.htm",
                        styleSheet="analysis.css",
                    )
                    table = page.table(
                        page.body(),
                        ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                    )
                    row = None
                    for m in range(8192):
                        if m % 10 == 0:
                            row = page.tableRow(table)
                            page.tableColumn(row, f"m{m}->")
                        var = pmac.hardwareState.getMVariable(m)
                        page.tableColumn(row, var.valStr())
                    for _i in range(8):
                        page.tableColumn(row, "")
                    page.write()
            # Dump the M variable values for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    page = WebPage(
                        "M Variable values for {} ({})".format(
                            pmac.name, datetime.today().strftime("%x %X")
                        ),
                        f"{self.config.resultsDir}/{pmac.name}_mvariablevalues.htm",
                        styleSheet="analysis.css",
                    )
                    table = page.table(
                        page.body(),
                        ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                    )
                    row = None
                    for m in range(8192):
                        if m % 10 == 0:
                            row = page.tableRow(table)
                            page.tableColumn(row, f"m{m}")
                        mvar = cast(PmacMVariable, (pmac.hardwareState.getMVariable(m)))
                        page.tableColumn(row, mvar.contentsStr())
                    for _i in range(8):
                        page.tableColumn(row, "")
                    page.write()
            # Dump the P variables for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    page = WebPage(
                        "P Variables for {} ({})".format(
                            pmac.name, datetime.today().strftime("%x %X")
                        ),
                        f"{self.config.resultsDir}/{pmac.name}_pvariables.htm",
                        styleSheet="analysis.css",
                    )
                    table = page.table(
                        page.body(),
                        ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                    )
                    row = None
                    for m in range(8192):
                        if m % 10 == 0:
                            row = page.tableRow(table)
                            page.tableColumn(row, f"p{m}")
                        var = pmac.hardwareState.getPVariable(m)
                        page.tableColumn(row, var.valStr())
                    for _i in range(8):
                        page.tableColumn(row, "")
                    page.write()
            # Dump the PLCs for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    # Create the PLC top level web page
                    page = WebPage(
                        "PLCs for {} ({})".format(
                            pmac.name, datetime.today().strftime("%x %X")
                        ),
                        f"{self.config.resultsDir}/{pmac.name}_plcs.htm",
                        styleSheet="analysis.css",
                    )
                    table = page.table(page.body(), ["PLC", "Code", "P Variables"])
                    for id in range(32):
                        plc = pmac.hardwareState.getPlcProgramNoCreate(id)
                        row = page.tableRow(table)
                        page.tableColumn(row, f"{id}")
                        if plc is not None:
                            page.href(
                                page.tableColumn(row),
                                f"{pmac.name}_plc_{id}.htm",
                                "Code",
                            )
                        else:
                            page.tableColumn(row, "-")
                        page.href(
                            page.tableColumn(row),
                            f"{pmac.name}_plc{id}_p.htm",
                            "P%d..%d" % (id * 100, id * 100 + 99),
                        )
                    page.write()
                    # Create the listing pages
                    for id in range(32):
                        plc = pmac.hardwareState.getPlcProgramNoCreate(id)
                        if plc is not None:
                            page = WebPage(
                                f"{pmac.name} PLC{id}",
                                f"{self.config.resultsDir}/{pmac.name}_plc_{id}.htm",
                                styleSheet="analysis.css",
                            )
                            plc.html2(page, page.body())
                            page.write()
                    # Create the P variable pages
                    for id in range(32):
                        page = WebPage(
                            f"P Variables for {pmac.name} PLC {id}",
                            f"{self.config.resultsDir}/{pmac.name}_plc{id}_p.htm",
                            styleSheet="analysis.css",
                        )
                        table = page.table(
                            page.body(),
                            ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                        )
                        row = None
                        for m in range(100):
                            if m % 10 == 0:
                                row = page.tableRow(table)
                                page.tableColumn(row, "p%s" % (m + id * 100))
                            var = pmac.hardwareState.getPVariable(m + id * 100)
                            page.tableColumn(row, var.valStr())
                        page.write()
            # Dump the motion programs for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    # Create the motion program top level web page
                    page = WebPage(
                        "Motion Programs for {} ({})".format(
                            pmac.name, datetime.today().strftime("%x %X")
                        ),
                        f"{self.config.resultsDir}/{pmac.name}_motionprogs.htm",
                        styleSheet="analysis.css",
                    )
                    table = page.table(page.body())
                    for id in range(256):
                        prog = pmac.hardwareState.getMotionProgramNoCreate(id)
                        if prog is not None:
                            row = page.tableRow(table)
                            page.tableColumn(row, f"prog{id}")
                            page.href(
                                page.tableColumn(row),
                                f"{pmac.name}_prog_{id}.htm",
                                "Code",
                            )
                    page.write()
                    # Create the listing pages
                    for id in range(256):
                        prog = pmac.hardwareState.getMotionProgramNoCreate(id)
                        if prog is not None:
                            page = WebPage(
                                f"Motion Program {id} for {pmac.name}",
                                f"{self.config.resultsDir}/{pmac.name}_prog_{id}.htm",
                                styleSheet="analysis.css",
                            )
                            prog.html2(page, page.body())
                            page.write()
            # Dump the coordinate systems for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    # Create the coordinate systems top level web page
                    page = WebPage(
                        "Coordinate Systems for {} ({})".format(
                            pmac.name, datetime.today().strftime("%x %X")
                        ),
                        f"{self.config.resultsDir}/{pmac.name}_coordsystems.htm",
                        styleSheet="analysis.css",
                    )
                    table = page.table(
                        page.body(),
                        [
                            "CS",
                            "Axis def",
                            "Forward Kinematic",
                            "Inverse Kinematic",
                            "Q Variables",
                            "%",
                        ],
                    )
                    for id in range(1, 17):
                        row = page.tableRow(table)
                        page.tableColumn(row, f"{id}")
                        col = page.tableColumn(row)
                        for m in range(1, 33):
                            var = pmac.hardwareState.getCsAxisDefNoCreate(id, m)
                            if var is not None and not var.isZero():
                                page.text(col, f"#{m}->")
                                var.html(page, col)
                        col = page.tableColumn(row)
                        var = pmac.hardwareState.getForwardKinematicProgramNoCreate(id)
                        if var is not None:
                            var.html(page, col)
                        col = page.tableColumn(row)
                        var = pmac.hardwareState.getInverseKinematicProgramNoCreate(id)
                        if var is not None:
                            var.html(page, col)
                        page.href(
                            page.tableColumn(row),
                            f"{pmac.name}_cs{id}_q.htm",
                            "Q Variables",
                        )
                        col = page.tableColumn(row)
                        var = pmac.hardwareState.getFeedrateOverrideNoCreate(id)
                        if var is not None:
                            var.html(page, col)
                    page.write()
                    for id in range(1, 17):
                        page = WebPage(
                            f"Q Variables for {pmac.name} CS {id}",
                            f"{self.config.resultsDir}/{pmac.name}_cs{id}_q.htm",
                            styleSheet="analysis.css",
                        )
                        table = page.table(
                            page.body(),
                            ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                        )
                        row = None
                        for m in range(100):
                            if m % 10 == 0:
                                row = page.tableRow(table)
                                page.tableColumn(row, f"q{m}")
                            var = pmac.hardwareState.getQVariable(id, m)
                            page.tableColumn(row, var.valStr())
                        page.write()
            self.hudsonXmlReport()

    def loadFactorySettings(self, pmac, fileName, includeFiles):
        for i in range(8192):
            pmac.getIVariable(i)
        for m in range(8192):
            pmac.getMVariable(m)
        for p in range(8192):
            pmac.getPVariable(p)
        for cs in range(1, 17):
            for m in range(1, 33):
                pmac.getCsAxisDef(cs, m)
            for q in range(1, 200):
                pmac.getQVariable(cs, q)
        pmac.loadPmcFileWithPreprocess(fileName, includeFiles)

    def hudsonXmlReport(self):
        # Write out an XML report for Hudson
        xmlDoc = getDOMImplementation().createDocument(None, "testsuite", None)  # noqa
        xmlTop = xmlDoc.documentElement
        xmlTop.setAttribute("tests", str(len(self.config.pmacs)))
        xmlTop.setAttribute("time", "0")
        xmlTop.setAttribute("timestamp", "0")
        for name, pmac in self.config.pmacs.items():
            element = xmlDoc.createElement("testcase")
            xmlTop.appendChild(element)
            element.setAttribute("classname", "pmac")
            element.setAttribute("name", name)
            element.setAttribute("time", "0")
            if not pmac.compareResult:
                errorElement = xmlDoc.createElement("error")
                element.appendChild(errorElement)
                errorElement.setAttribute("message", "Compare mismatch")
                textNode = xmlDoc.createTextNode(
                    f"See file:///{self.config.resultsDir}/index.htm for details"
                )
                errorElement.appendChild(textNode)
        wFile = open(f"{self.config.resultsDir}/report.xml", "w")
        xmlDoc.writexml(wFile, indent="", addindent="  ", newl="\n")
