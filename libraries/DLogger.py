import datetime

class DLogger:
    # version 4
    def __init__(self, 
        print = True, 
        logfile = False, 
        log_filename="log.txt", 
        include_log_level = True):

        self.lgs = []  # logging entries
        self.timers = []
        self.log_channels = []
        self.include_log_level = include_log_level 
        if print:
            self.log_channels.append("print")
        if logfile:
            self.log_channels.append("logfile")
            self.log_filename = log_filename
    
    def remove_channel(self, channel):
        if channel in self.log_channels:
            self.log_channels.remove(channel)
        else:
            self.log("Channel '" + channel + "' not found in log channels", 2)

    def log(self, message, loglevel=1, type="info"):
        now = datetime.datetime.now()
        log = {'time': now, 'text': message, 'level': loglevel, 'type': type}
        self.lgs.append(log)
        for channel in self.log_channels:
            if channel == "print":
                print(self.getlogstring(log))
            elif channel == "logfile":
                pass

    def getlogstring(self, logitem):
        then = logitem['time']
        # dtd = then.strftime("%d.%m.%y") # date
        log_string = then.strftime("%H:%M:%S") + ": "  # time
        # dtms = then.strftime("%f\u00B5s") # microseconds
        if self.include_log_level:
            log_string += " "*int(logitem['level'])
            log_string += '(' + str(logitem['level']) + ') ' 
        log_string += logitem['text']
        # string = str(logitem['time']) + ': ('+ str(logitem['level'])+') ' + logitem['text']
        return log_string


    def getloglines(self, nums=0, breakc='\n'):
        text = ""
        for i in self.lgs[-nums:]:
            text += self.getlogstring(i) + breakc
        return text

    def getloglineshtml(self, nums=0, ):
        htmlt = []
        for i in self.lgs[-nums:]:
            # then = i['time']
            # dtd = then.strftime("%d.%m.%y")
            # dtt = then.strftime("%H:%M:%S")
            # dtms = then.strftime("%f\u00B5s")
            # text = dtt + ': (' + str(i['level'])+') ' + i['text']
            text = self.getlogstring(i)
            #htmlt.append(html.Div(text))
            htmlt.append("<div>"+text+"</div>")
        return htmlt

    def getloghtml(self):
        return "\n".join(self.getloglineshtml())

    def opennewtimer(self):
        self.timers.append(datetime.datetime.now())

    def closelasttimer(self):
        td = datetime.datetime.now() - self.timers[-1]
        secs = td.seconds
        if secs:
            tds = str(td.seconds) + ',' + str(td.microseconds) + "s"
        else:
            tds = str(td.microseconds) + "\u00B5s"
        del self.timers[-1]
        return tds
