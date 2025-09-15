import pickle
from multiprocessing import Lock
import os

from src.LoggingServer import LoggingServer

class UserOptionsManager():

    
    def __init__(self, optionsFile = "./resources/options.pkl"):
        self._optionsFile = optionsFile
        self._lock = Lock()
        # Ensure file exists
        os.makedirs(os.path.dirname(self._optionsFile), exist_ok=True)
        if not os.path.exists(self._optionsFile):
            with open(self._optionsFile, "wb") as f:
                pickle.dump({}, f)
    
    def getDpiOption(self, userId):
        try:
            userOptions = self.getUserOptions(userId)
        except KeyError:
            userOptions = self.getDefaultUserOptions()
        try:
            return userOptions['dpi']
        except KeyError:
            return self.getDefaultUserOptions()["dpi"]
        
    def setDpiOption(self, userId, value):
        try:
            userOptions = self.getUserOptions(userId)
        except KeyError:
            userOptions = self.getDefaultUserOptions()
        userOptions['dpi'] = value
        self.setUserOptions(userId, userOptions)
        
    def getCodeInCaptionOption(self, userId):
        try:
            userOptions = self.getUserOptions(userId)
        except KeyError:
            userOptions = self.getDefaultUserOptions()
        return userOptions['show_code_in_caption']
        
    def setCodeInCaptionOption(self, userId, value):
        try:
            userOptions = self.getUserOptions(userId)
        except KeyError:
            userOptions = self.getDefaultUserOptions()
        userOptions['show_code_in_caption'] = value
        self.setUserOptions(userId, userOptions)
        
    def getUserOptions(self, userId):
        with self._lock:
            with open(self._optionsFile, "rb") as f:
                userOptions = pickle.load(f)[userId]
            return userOptions
    
    def setUserOptions(self, userId, userOptions):
        with self._lock:
            with open(self._optionsFile, "rb") as f:
                options = pickle.load(f)
            options[userId] = userOptions
            with open(self._optionsFile, "wb") as f:
                pickle.dump(options, f)
        
    def getDefaultUserOptions(self):
        # Default HTML format can be overridden via env var
        html_fmt = os.environ.get("LATEXBOT_HTML_FORMAT", "html5")
        make4ht_args = os.environ.get("LATEXBOT_MAKE4HT_ARGS", "")
        return {'show_code_in_caption': False, "dpi":300, "html_format": html_fmt, "make4ht_args": make4ht_args}

    # ----------------- HTML format option -----------------
    def getHtmlFormatOption(self, userId):
        try:
            userOptions = self.getUserOptions(userId)
        except KeyError:
            userOptions = self.getDefaultUserOptions()
        try:
            return userOptions['html_format']
        except KeyError:
            return self.getDefaultUserOptions()['html_format']

    def setHtmlFormatOption(self, userId, value: str):
        try:
            userOptions = self.getUserOptions(userId)
        except KeyError:
            userOptions = self.getDefaultUserOptions()
        userOptions['html_format'] = value
        self.setUserOptions(userId, userOptions)

    # ----------------- make4ht args option -----------------
    def getMake4htArgsOption(self, userId) -> str:
        try:
            userOptions = self.getUserOptions(userId)
        except KeyError:
            userOptions = self.getDefaultUserOptions()
        try:
            return userOptions['make4ht_args']
        except KeyError:
            return self.getDefaultUserOptions()['make4ht_args']

    def setMake4htArgsOption(self, userId, value: str):
        try:
            userOptions = self.getUserOptions(userId)
        except KeyError:
            userOptions = self.getDefaultUserOptions()
        userOptions['make4ht_args'] = value or ""
        self.setUserOptions(userId, userOptions)
