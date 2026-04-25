import datetime
import glob
import os
import logging


class LoggerManager:
    def __init__(self, nameModule=__name__):
        self.nameModule = nameModule
        self.logPath = self._getLogsPath()
        self._cleanLogs()
        self.logger = self._configLogger()

    def _getLogsPath(self):
        path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__), "../../logs", f"{self.nameModule}_log"
            )
        )
        os.makedirs(path, exist_ok=True)
        return path

    def _erraseLogs(self, today):
        oldLogs = glob.glob(os.path.join(self.logPath, "*.log"))
        for log in oldLogs:
            if str(today) not in log:
                try:
                    os.remove(log)
                except Exception as e:
                    print(f"Error removing old log {log}: {e}")

    def _cleanLogs(self):
        today = datetime.date.today()

        if today.weekday() == 0:
            self._erraseLogs(today)

    def _configLogger(self):
        today = datetime.date.today()
        pathLogs = os.path.join(self.logPath, f"{today}.log")

        logger = logging.getLogger(self.nameModule)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            formatLogging = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            )
            logHandler = logging.FileHandler(pathLogs, mode="a", encoding="utf-8")
            logHandler.setFormatter(formatLogging)

            streamHandler = logging.StreamHandler()
            streamHandler.setFormatter(formatLogging)

            logger.addHandler(logHandler)
            logger.addHandler(streamHandler)

        return logger

    def getLogger(self):
        return self.logger
