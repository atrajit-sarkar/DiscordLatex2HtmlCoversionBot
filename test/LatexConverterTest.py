import unittest
from unittest.mock import Mock

import os
from datetime import datetime as dt
from subprocess import check_output, CalledProcessError, STDOUT
from unittest.mock import patch

from src.LatexConverter import LatexConverter
from src.PreambleManager import PreambleManager
from src.ResourceManager import ResourceManager
from src.UserOptionsManager import UserOptionsManager

class LatexConverterTest(unittest.TestCase):

    def setUp(self):
        userOptionsManager = Mock()
        userOptionsManager.getDpiOption = Mock(return_value = 720)
        self.sut = LatexConverter(PreambleManager(ResourceManager()), userOptionsManager)

    def testExtractBoundingBox(self):
        self.sut.logger.debug("Extracting bbox")
        self.sut.extractBoundingBox(720, "resources/test/bbox.pdf")
        self.sut.logger.debug("Extracted bbox")
    
    def testCorrectBoundingBoxAspectRaito(self):
        pass
    
    def testPdflatex(self):
        self.sut.logger.debug("Started pdflatex")
        self.sut.pdflatex("resources/test/pdflatex.tex")
        self.sut.logger.debug("Pdflatex finished")

        try: 
            self.sut.pdflatex("resources/test/pdflatexwerror.tex")
        except ValueError as err:
            self.assertEqual(err.args[0], "! Missing lol inserted\nasldkasdaskd;laskd;a\n")
            
        check_output(["rm build/pdflatex*"], stderr=STDOUT, shell=True)

    def testPdflatexHangupHandling(self):
        try:
            self.sut.pdflatex("resources/test/pdflatex_hanging_file.tex")
            raise AssertionError("Should not reach this point!")
        except ValueError as err:
            self.assertEqual(err.args[0], "Pdflatex has likely hung up and had to be killed. Congratulations!")
        finally:
            check_output(["rm build/pdflatex_hanging_file*"], stderr=STDOUT, shell=True)

    def testConvertExpressionToPng(self):
        binaryData = self.sut.convertExpression("$x^2$", 115, "id").read()
        with open('resources/test/xsquared.png', "rb") as f:
            correctBinaryData = f.read()
        self.assertAlmostEqual(len(binaryData), len(correctBinaryData), delta=50)
        
        binaryData = self.sut.convertExpression("$x^2$" * 10, 115, "id").read()
        with open('resources/test/xsquared10times.png', "rb") as f:
            correctBinaryData = f.read()
        self.assertAlmostEqual(len(binaryData), len(correctBinaryData), delta=50)
        
    def testDeleteFilesInAllCases(self):
        self.sut.convertExpression("$x^2$", 115, "id")
        files = os.listdir("build/")

        try:
            self.assertEqual(len(files), 0)
        except AssertionError:
            print(files)
            raise
        
        try:
            self.sut.convertExpression("$$$$", 115, "id1").read()
        except ValueError:
            self.assertEqual(len(os.listdir("build/")), 0)
        
        try:
            self.sut.convertExpression(r"lo \asdasd", 115, "id2").read()
        except ValueError:
            self.assertEqual(len(os.listdir("build/")), 0)
    
    def testEmptyQuery(self):
        with self.assertRaises(ValueError):
            self.sut.convertExpression("$$$$", 115, "id").read()

        with self.assertRaises(ValueError):
            self.sut.convertExpression(" %comment", 115, "id").read()

    def testIgnoreInternalPreambles(self):
        self.sut.convertExpression(r"\documentclass{article} \begin{document} \LaTeX \end{document}", 115, "id")

    def testReturnPdf(self):
        pdfBinaryData = self.sut.convertExpression("lol", 115, "id", True)[1].read()
        with open('resources/test/cropped.pdf', "rb") as f:
            correctBinaryData = f.read()
        self.assertAlmostEqual(len(pdfBinaryData), len(correctBinaryData), delta=50)

    def testConvertToHtml_mocked(self):
        # Mock out external converter call and create a dummy HTML
        with patch.object(self.sut, '_run_tex_to_html', return_value=None):
            # We also need to ensure that after _run_tex_to_html the workdir contains an HTML file
            userId = 115
            sessionId = "ziptest"
            # Prepare by intercepting os.path.exists in a minimal scope is messy; instead, run and then place a fake file
            # We'll simulate by calling convertToHtml, but we need to inject an HTML creation step; easiest is to monkeypatch os.path.exists
            # Instead, call internal methods by replicating minimal workflow
            import os, io, zipfile
            workdir = os.path.join("build", f"html_{sessionId}")
            try:
                os.makedirs(workdir, exist_ok=True)
                with open(os.path.join(workdir, 'document.html'), 'w', encoding='utf-8') as f:
                    f.write("<html><body><p>ok</p></body></html>")
                # Now run convertToHtml which will package contents and cleanup
                z = self.sut.convertToHtml("$x$", userId, sessionId)
                data = z.read()
                self.assertTrue(len(data) > 50)
                # Validate zip has index.html
                z.seek(0)
                with zipfile.ZipFile(z, 'r') as zf:
                    names = zf.namelist()
                    self.assertTrue(any(n.endswith('index.html') or n.endswith('document.html') for n in names))
            finally:
                try:
                    import shutil
                    shutil.rmtree(workdir, ignore_errors=True)
                except Exception:
                    pass
       
    #def testPrivacySettings(self):
    #    self.sut.logger.debug("Started pdflatex")
    #    self.sut.pdflatex("resources/test/privacy.tex")
    #    self.sut.logger.debug("Pdflatex finished")
    
#    def testPerformance(self):
#        self.sut.logger.debug("Started performance test")
#        start = dt.now()
#        for i in range(0, 10):
#            self.sut.convertExpressionToPng("$x^2$", 115, "id")
#        elapsedTime = (dt.now()-start).total_seconds()/10*1000
#        self.sut.logger.debug("Performance test ended, time: %f ms", elapsedTime)
        
if __name__ == '__main__':
    test = LatexConverterTest()
    test.setUp()
    test.testPerformance()
#    unittest.main()
    
