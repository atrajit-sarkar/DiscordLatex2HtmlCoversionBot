from subprocess import check_output, CalledProcessError, STDOUT, TimeoutExpired

from src.PreambleManager import PreambleManager
from src.LoggingServer import LoggingServer
import io
import re
import shutil
import os
import glob


class LatexConverter():

    logger = LoggingServer.getInstance()
    
    def __init__(self, preambleManager, userOptionsManager):
         self._preambleManager = preambleManager
         self._userOptionsManager = userOptionsManager

    def extractBoundingBox(self, dpi, pathToPdf):
        try:
            gs = self._get_gs_executable()
            bbox = check_output([gs, "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=bbox", pathToPdf],
                                stderr=STDOUT).decode("ascii")
        except CalledProcessError:
            raise ValueError("Could not extract bounding box! Empty expression?")
        except FileNotFoundError:
            raise ValueError("Ghostscript not found. Please install Ghostscript and ensure 'gs', 'gswin64c' or 'gswin32c' is on PATH.")
        try:
            bounds = [int(_) for _ in bbox[bbox.index(":")+2:bbox.index("\n")].split(" ")]
        except ValueError:
            raise ValueError("Could not parse bounding box! Empty expression?")

        if bounds[0] == bounds[2] or bounds[1] == bounds[3]:
            self.logger.warn("Expression had zero width/height bbox!")
            raise ValueError("Empty expression!")

        hpad = 0.25 * 72  # 72 postscript points = 1 inch
        vpad = .1 * 72
        llc = bounds[:2]
        llc[0] -= hpad
        llc[1] -= vpad
        ruc = bounds[2:]
        ruc[0] += hpad
        ruc[1] += vpad
        size_factor = dpi/72
        width = (ruc[0]-llc[0])*size_factor
        height = (ruc[1]-llc[1])*size_factor
        translation_x = llc[0]
        translation_y = llc[1]
        return width, height, -translation_x, -translation_y
    
    def correctBoundingBoxAspectRaito(self, dpi, boundingBox, maxWidthToHeight=3, maxHeightToWidth=1):
        width, height, translation_x, translation_y = boundingBox
        size_factor = dpi/72
        if width>maxWidthToHeight*height:
            translation_y += (width/maxWidthToHeight-height)/2/size_factor
            height = width/maxWidthToHeight
        elif height>maxHeightToWidth*width:
            translation_x += (height/maxHeightToWidth-width)/2/size_factor
            width = height/maxHeightToWidth
        return width, height, translation_x, translation_y
        
    def getError(self, log):
        for idx, line in enumerate(log):
            if line[:2]=="! ":
                return "".join(log[idx:idx+2])
        
    def pdflatex(self, fileName):
        try:
            check_output([
                'pdflatex',
                '-interaction=nonstopmode',
                '-output-directory', 'build',
                fileName
            ], stderr=STDOUT, timeout=5)
        except CalledProcessError:
            with open(fileName[:-3] + "log", "r") as f:
                msg = self.getError(f.readlines())
                self.logger.debug(msg)
            raise ValueError(msg)
        except TimeoutExpired:
            msg = "Pdflatex has likely hung up and had to be killed. Congratulations!"
            raise ValueError(msg)
    
    def cropPdf(self, sessionId): # TODO: this is intersecting with the png part
        try:
            gs = self._get_gs_executable()
            bbox = check_output([gs, "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=bbox", f"build/expression_file_{sessionId}.pdf"], 
                                stderr=STDOUT).decode("ascii")
        except FileNotFoundError:
            raise ValueError("Ghostscript not found. Please install Ghostscript and ensure it is on PATH.")
        llx, lly, urx, ury = tuple([int(_) for _ in bbox[bbox.index(":")+2:bbox.index("\n")].split(" ")])
        # Add configurable margin (points). Default 24pt (~1/3 inch) for comfortable whitespace.
        try:
            margin = float(os.environ.get("LATEXBOT_PDF_MARGIN_PT", "24"))
        except ValueError:
            margin = 24.0
        margin = max(0.0, margin)
        # Expand bbox by margin on all sides
        width_pts = (urx - llx) + int(2 * margin)
        height_pts = (ury - lly) + int(2 * margin)
        # Translate content so that original lower-left is at (margin, margin)
        offset_x = -llx + int(margin)
        offset_y = -lly + int(margin)
        out_pdf = f"build/expression_file_cropped_{sessionId}.pdf"
        in_pdf = f"build/expression_file_{sessionId}.pdf"
        # Set exact page size and translate content so the expression sits at origin
        try:
            check_output([gs, "-o", out_pdf, "-sDEVICE=pdfwrite",
                          f"-dDEVICEWIDTHPOINTS={width_pts}", f"-dDEVICEHEIGHTPOINTS={height_pts}", "-dFIXEDMEDIA",
                          "-c", f"<</PageOffset [{offset_x} {offset_y}]>> setpagedevice",
                          "-f", in_pdf], stderr=STDOUT)
        except FileNotFoundError:
            raise ValueError("Ghostscript not found. Please install Ghostscript and ensure it is on PATH.")
            
    def convertPdfToPng(self, dpi, sessionId, bbox):
        gs = self._get_gs_executable()
        out_png = f"build/expression_{sessionId}.png"
        in_pdf = f"build/expression_file_{sessionId}.pdf"
        width, height, tx, ty = bbox
        # Default to white background to avoid black/transparent appearance in some viewers.
        transparent = os.environ.get("LATEXBOT_TRANSPARENT", "").lower() in ("1", "true", "yes", "on")
        device = "pngalpha" if transparent else "png16m"
        args = [gs, "-o", out_png, f"-r{dpi}", f"-g{int(width)}x{int(height)}", "-dLastPage=1",
                "-sDEVICE=" + device,
                "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
                "-c", f"<</Install {{{int(tx)} {int(ty)} translate}}>> setpagedevice",
                "-f", in_pdf]
        if not transparent:
            # White background for non-alpha device
            args.insert(6, "-dBackgroundColor=16#FFFFFF")
        try:
            check_output(args, stderr=STDOUT)
        except FileNotFoundError:
            raise ValueError("Ghostscript not found. Please install Ghostscript and ensure it is on PATH.")

    def convertExpression(self, expression, userId, sessionId, returnPdf = False):




        if r"\documentclass" in expression:
            fileString = expression
        else:
            try:
                preamble = self._preambleManager.getPreambleFromDatabase(userId)
                self.logger.debug("Preamble for userId %d found", userId)
            except KeyError:
                self.logger.debug("Preamble for userId %d not found, using default preamble", userId)
                preamble = self._preambleManager.getDefaultPreamble()
            finally:
                fileString = preamble+"\n\\begin{document}\n"+expression+"\n\\end{document}"

        os.makedirs("build", exist_ok=True)
        with open("build/expression_file_%s.tex"%sessionId, "w+") as f:
            f.write(fileString)
        
        dpi = self._userOptionsManager.getDpiOption(userId)
        
        try:
            try:
                self.pdflatex("build/expression_file_%s.tex"%sessionId)
            except FileNotFoundError:
                raise ValueError("pdflatex not found. Please install a LaTeX distribution (TeX Live or MiKTeX) and ensure 'pdflatex' is on PATH.")
                
            bbox = self.extractBoundingBox(dpi, "build/expression_file_%s.pdf"%sessionId)
            bbox = self.correctBoundingBoxAspectRaito(dpi, bbox)
            self.convertPdfToPng(dpi, sessionId, bbox)
            
            self.logger.debug("Generated image for %s", expression)
            
            with open("build/expression_%s.png"%sessionId, "rb") as f:
                imageBinaryStream = io.BytesIO(f.read())

            if returnPdf:
                is_full_document = (r"\documentclass" in expression)
                if is_full_document:
                    # Preserve full document layout and margins
                    with open("build/expression_file_%s.pdf"%sessionId, "rb") as f:
                        pdfBinaryStream = io.BytesIO(f.read())
                else:
                    self.cropPdf(sessionId)
                    with open("build/expression_file_cropped_%s.pdf"%sessionId, "rb") as f:
                        pdfBinaryStream = io.BytesIO(f.read())
                return imageBinaryStream, pdfBinaryStream
            else:
                return imageBinaryStream
                
        finally:
            # Cross-platform cleanup
            try:
                for f in glob.glob(os.path.join("build", f"*_{sessionId}.*")):
                    try:
                        os.remove(f)
                    except FileNotFoundError:
                        pass
            except Exception:
                pass

    def _get_gs_executable(self):
        # Try common Ghostscript executables across platforms
        for name in ("gs", "gswin64c", "gswin32c"):
            path = shutil.which(name)
            if path:
                return path
        # Fallback to 'gs' which will raise later if missing
        return "gs"

    # -------------------------- HTML (TeX4ht) conversion --------------------------
    def _get_htlatex_executable(self):
        # Prefer make4ht (supports -f formats and extra args), fall back to htlatex
        make4ht = shutil.which("make4ht")
        if make4ht:
            return make4ht
        path = shutil.which("htlatex")
        if path:
            # Try to find make4ht in the same directory as htlatex as a fallback
            try:
                base_dir = os.path.dirname(path)
                for cand in ("make4ht.exe", "make4ht.bat", "make4ht"):
                    candidate = os.path.join(base_dir, cand)
                    if os.path.exists(candidate):
                        return candidate
            except Exception:
                pass
            return path
        return None

    def _run_tex_to_html(self, tex_path: str, workdir: str, timeout: int = 30, html_format: str | None = None, make4ht_args: list[str] | None = None):
        """Run TeX→HTML using htlatex (preferred) or make4ht in the given workdir.
        Raises ValueError with a helpful message on failure.
        """
        # Allow overriding timeout via environment for heavy docs (e.g., TikZ)
        try:
            env_timeout = int(os.environ.get("LATEXBOT_HTML_TIMEOUT", "0"))
            if env_timeout > 0:
                timeout = env_timeout
        except Exception:
            pass
        exe = self._get_htlatex_executable()
        if not exe:
            raise ValueError("htlatex/make4ht not found. Please install TeX Live and ensure 'htlatex' (or 'make4ht') is on PATH.")

        # Determine desired output format (for make4ht). Default from env if not provided.
        if not html_format:
            html_format = os.environ.get("LATEXBOT_HTML_FORMAT", "html5").strip()
        # Basic allowlist of common formats
        allowed_formats = {"html5", "html5+mathjax", "xhtml", "odt", "epub"}
        if html_format not in allowed_formats:
            # Fall back to html5 if unsupported, but keep informative message
            self.logger.warn("Unsupported HTML format '%s' requested; falling back to 'html5'", html_format)
            html_format = "html5"

        exe_name = os.path.basename(exe).lower() if exe else ""
        try:
            if exe_name.startswith("make4ht"):
                # make4ht handles modern setups well
                # Command: make4ht -u -f <format> [extensions/args...] texfile.tex
                # Support html_format like 'html5+mathjax' by splitting into base format and extension tokens
                base_fmt = html_format
                ext_tokens: list[str] = []
                if "+" in html_format:
                    parts = html_format.split("+")
                    base_fmt = parts[0]
                    ext_tokens.extend(parts[1:])
                cmd = [exe, "-u", "-f", base_fmt]
                # Split user args into options (start with '-') and potential extension tokens
                opt_args: list[str] = []
                user_exts: list[str] = []
                if make4ht_args:
                    for a in make4ht_args:
                        if isinstance(a, str) and a.startswith("-"):
                            opt_args.append(a)
                        else:
                            # treat as extension token (e.g., 'mathjax')
                            user_exts.append(str(a))
                # Add options before filename
                if opt_args:
                    cmd.extend(opt_args)
                # Add input filename before extensions per make4ht usage
                cmd.append(os.path.basename(tex_path))
                # Merge extensions from format (ext_tokens) and user-supplied tokens
                all_exts = ext_tokens + user_exts
                # Prefer SVG output for figures with dvisvgm and stable names; only for HTML targets
                if base_fmt in ("html5", "xhtml"):
                    if "svg" not in all_exts:
                        all_exts.append("svg")
                    if "dvisvgm_hashes" not in all_exts:
                        all_exts.append("dvisvgm_hashes")
                if all_exts:
                    ext_str = ",".join(all_exts)
                    cmd.append(ext_str)
                check_output(cmd, cwd=workdir, stderr=STDOUT, timeout=timeout)
            else:
                # htlatex basic invocation; defaults to generating texbase.html
                check_output([exe, os.path.basename(tex_path)], cwd=workdir, stderr=STDOUT, timeout=timeout)
        except CalledProcessError as e:
            # Try to surface a clear error from logs or command output
            base = os.path.splitext(os.path.basename(tex_path))[0]
            candidates = [base + ".log", base + ".lg", base + ".ht4ht"]
            log_excerpt = None
            for cand in candidates:
                p = os.path.join(workdir, cand)
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                        # Prefer the LaTeX-style error starting with '! '
                        latex_err = self.getError(lines)
                        if latex_err:
                            log_excerpt = latex_err
                            break
                        # Otherwise include the last ~40 lines as context
                        tail = "".join(lines[-40:])
                        if tail.strip():
                            log_excerpt = tail
                            break
                    except Exception:
                        pass
            output_tail = None
            try:
                output_tail = (e.output or b"").decode("utf-8", errors="ignore").splitlines()[-40:]
                output_tail = "\n".join(output_tail)
            except Exception:
                output_tail = None
            msg_parts = [f"TeX4ht ({'make4ht' if exe_name.startswith('make4ht') else 'htlatex'}) failed."]
            if log_excerpt:
                msg_parts.append("Log excerpt:\n" + log_excerpt)
            if output_tail:
                msg_parts.append("Command output (tail):\n" + output_tail)
            raise ValueError("\n\n".join(msg_parts))
        except TimeoutExpired:
            raise ValueError("htlatex/make4ht timed out while converting to HTML.")

    def convertToHtml(self, expression: str, userId: int, sessionId: str, html_format: str | None = None, make4ht_args: list[str] | None = None):
        """Convert LaTeX input to an HTML website using TeX Live (htlatex/make4ht).

        Returns: BytesIO of a ZIP archive containing index.html and any assets.
        """
        # Build a full document if needed (reuse user's preamble)
        if r"\documentclass" in expression:
            fileString = expression
        else:
            try:
                preamble = self._preambleManager.getPreambleFromDatabase(userId)
                self.logger.debug("Preamble for userId %d found", userId)
            except KeyError:
                self.logger.debug("Preamble for userId %d not found, using default preamble", userId)
                preamble = self._preambleManager.getDefaultPreamble()
            finally:
                fileString = preamble+"\n\\begin{document}\n"+expression+"\n\\end{document}"

        workdir = os.path.join("build", f"html_{sessionId}")
        os.makedirs(workdir, exist_ok=True)
        tex_base = "document"
        tex_path = os.path.join(workdir, tex_base + ".tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(fileString)

        try:
            # Run converter
            self._run_tex_to_html(tex_path, workdir, html_format=html_format, make4ht_args=make4ht_args)

            # Determine produced HTML file (htlatex uses the base name)
            produced_html = os.path.join(workdir, tex_base + ".html")
            if not os.path.exists(produced_html):
                # make4ht may choose different extensions, fallback to first html in dir
                htmls = [p for p in glob.glob(os.path.join(workdir, "*.html"))]
                if htmls:
                    produced_html = htmls[0]
                else:
                    raise ValueError("HTML output not found after conversion.")

            # Rename to index.html for nicer website packaging
            index_html = os.path.join(workdir, "index.html")
            if os.path.abspath(produced_html) != os.path.abspath(index_html):
                try:
                    os.replace(produced_html, index_html)
                except Exception:
                    # Fallback to copy
                    try:
                        with open(produced_html, "rb") as src, open(index_html, "wb") as dst:
                            dst.write(src.read())
                    except Exception:
                        index_html = produced_html  # keep original name

            # Package directory into a ZIP in-memory
            import zipfile, io as _io
            zip_stream = _io.BytesIO()
            with zipfile.ZipFile(zip_stream, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(workdir):
                    for name in files:
                        full = os.path.join(root, name)
                        # Put files at archive root
                        arcname = os.path.relpath(full, workdir)
                        zf.write(full, arcname)
            zip_stream.seek(0)
            return zip_stream
        finally:
            # Clean working directory unless debugging is requested
            try:
                keep = os.environ.get("LATEXBOT_KEEP_HTML_TEMP", "").lower() in ("1", "true", "yes", "on")
                if not keep:
                    shutil.rmtree(workdir, ignore_errors=True)
            except Exception:
                pass
        
