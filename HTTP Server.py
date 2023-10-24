import socket, selectors, types, os, time, traceback

sel = selectors.DefaultSelector()
os.chdir(os.path.realpath(os.path.dirname(__file__)))

port = 80
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    lsock.bind(("", port))
    Error = 0
except OSError:
    Error = 1
if Error == 1:
    raise OSError(f"Theres already a program connected to \033[96mport {port}\33[0m")
lsock.listen()
print(f"\n\n\n\nListening on \033[96mport {port}\33[0m")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)
statusLength = 0
bannedList = {}
lastTick = 0
head = False

def FullPrint(*args, end="\n"):
    text = ""
    for i in args:
        text += str(i) + " "
    SpaceNum = os.get_terminal_size().columns - 1
    print(" " * SpaceNum, end = "\r")
    print(text, end=end)
def HTTPFormat(sock, code, *args, content=None):
    global head
    if content == None:
        content = b""
    msg = b"HTTP/1.1 "
    msg += bytes(code, "ascii") + b"\r\n"
    for arg in args:
        msg += bytes(arg, "ascii") + b"\r\n"
    msg += b"Content-Length: " + bytes(str(len(content)), "ascii")
    msg += b"\r\n\r\n"
    if head == False:
        msg += content
    sock.send(msg)
def addrConv(data):
    host = data.addr[0]
    port = str(data.addr[1])
    if host == "127.0.0.1":
        host = "LocalHost"
    return(f"\033[96m{host}({port})\33[0m", host)
def buffer():
    bufferSpeed = 0.2
    states = ["-", "\\", "|", "/"]
    return(states[round(time.time()//bufferSpeed % 4)])
def accept_wrapper(sock):
    conn, addr = sock.accept()
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, outb=b"", networkstate="Initializing", lastReq = "N/A", strikes = 0, state = "Normal", timeout = time.time())
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)
def service_connection(key, mask):
    global head
    sock = key.fileobj
    data = key.data
    addr, host = addrConv(data)
    try:
        # Banning and join message handling
        if host in bannedList.keys():
            HTTPFormat(sock, "429 Too Many Requests")
            sel.unregister(sock)
            sock.close()
            return()
        if data.networkstate == "Initializing":
            FullPrint(f"Accepted connection from {addr}")
            data.networkstate = "Connected"
            sel.modify(sock, selectors.EVENT_READ, data=data)
            return()
        
        data.timeout = time.time()
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)
            if recv_data:
                data.outb = recv_data
                sel.modify(sock, selectors.EVENT_WRITE, data=data)
            else:
                if data.networkstate in ["Initializing", "Connected", "Ready to Redirect"]:
                    FullPrint(f"{addr} pinged the server, then closed the connection")
                else:
                    FullPrint(f"Closing connection to {addr}")
                sel.unregister(sock)
                sock.close()

        if mask & selectors.EVENT_WRITE:
            sel.modify(sock, selectors.EVENT_READ, data=data)
            req = str(data.outb, "latin-1")
            data.outb = None
            command = req[0:req.find(" ")]
            param = req[len(command) + 1:req.find(" ", len(command) + 1)]
            # Last cmd handling
            if len(command) < 10:
                data.lastReq = command + " " + param
            else:
                data.lastReq = "400 Error, Invalid String"

            if req.find("HTTP/1.1") == -1 and req.find("HTTP/") != -1:
                FullPrint("An invalid HTTP version from " + addr + ":", req[req.find("HTTP/") + 5:req.find("HTTP/") + 8])
                HTTPFormat(sock, "505 HTTP Version Not Supported")
                data.strikes += 1
                return()

            # Invalid cmd handling
            if command not in ["GET", "HEAD"]:
                data.networkstate = "Arrived"
                # If the command is longer then 10, that might mean that the entire message is just a bytecode
                if len(command) < 10:
                    FullPrint("501 from " + addr + ":", command, param, "(...)")
                    HTTPFormat(sock, "501 Not Implemented")
                    data.strikes += 1
                else:
                    FullPrint("400 from " + addr + ": Command not specified (...)")
                    HTTPFormat(sock, "400 Bad Request")
                    data.strikes += 1
                if data.strikes == 5:
                    FullPrint(f"{addr} has been banned for 60 seconds")
                    bannedList[host] = time.time() + 60
                    sel.unregister(sock)
                    sock.close()

            else:
                if command == "HEAD":
                    head = True
                else:
                    head = False
                path = req[len(command) + 1:(req).find(" ", len(command) + 2)]
                if path == "/":
                    if data.networkstate == "Connected":
                        file = open(r"Discord.html","b+r")
                        HTTPFormat(sock, "200 OK", "Content-Type: text/html", content=file.read())
                        file.close()
                        data.networkstate = "Ready to Redirect"
                    else:
                        HTTPFormat(sock, "301 Moved Permanently", "Location: /index")
                        data.networkstate = "Redirecting"
                    return
                
                # If anything past this point is requested, they will no longer have the ping message when they leave
                data.networkstate = "Arrived"
                if path == "/index":
                    if data.networkstate == "Redirecting":
                        FullPrint(addr + " was redirected to the main website, and has arrived")
                    elif data.networkstate != "Arrived":
                        FullPrint(addr + " has connected to the main website")
                    else:
                        FullPrint(addr + " is refreshing their data", end="\r")
                    HTTPFormat(sock, "200 OK", "Content-Type: text/plain", content=b"This is a test of DanTCA Server Systems http connections.")
                    # file = open("C:/Users/danii/Downloads/test.html","b+r")
                    # HTTPFormat(sock, "200 OK", "Content-Type: text/html", content=file.read())
                    # file.close()

                elif path == "/favicon.ico":
                    if data.networkstate != "Arrived":
                        FullPrint(addr + " is retrieving a favicon")
                    else:
                        FullPrint(addr + " is refreshing their favicon", end="\r")
                    file = open("Favicon.png","b+r")
                    HTTPFormat(sock, "200 OK", "Content-Type: image/png", content=file.read())
                    file.close()

                else:
                    FullPrint("404 error from " + addr + ":", req[0: req.find(" ", 4)], "(...)")
                    HTTPFormat(sock, "404 Not Found")
                    data.strikes += 1
                    if data.strikes == 5:
                        FullPrint(f"{addr} has been banned for 60 seconds")
                        bannedList[host] = time.time() + 60
                        sel.unregister(sock)
                        sock.close()
                    

    except ConnectionResetError:
        FullPrint(f"{addr} forcefully closed the connection")
        sel.unregister(sock)
        sock.close()
    except Exception as error:
        for _ in range(statusLength):
            FullPrint()
        for _ in range(statusLength):
            print("\033[F", end="")
        FullPrint(f"Closing connection to {addr} due to server error")
        traceback.print_exception(error)
        HTTPFormat(sock, "500 Internal Server Error")
        sel.unregister(sock)
        sock.close()
def tick(): 
    global lastTick
    keys = sel.get_map()
    # Less often checks (every 5 seconds)
    if time.time() - lastTick >= 5:
        lastTick = time.time()
        #Timeout check
        keyscopy = dict(keys)
        for key in keyscopy.values():
            sock = key.fileobj
            data = key.data
            if data:
                timeout = time.time() - data.timeout
                if timeout > 120:
                    addr, _ = addrConv(data)
                    FullPrint(f"{addr} timed out")
                    HTTPFormat(sock, "408 Request Timeout")
                    sel.unregister(sock)
                    sock.close()
    # All the code for the status indicator
    global statusLength
    for _ in range(statusLength):
        FullPrint()
    for _ in range(statusLength):
        print("\033[F", end="")
    statusLength = 3
    FullPrint("-" * (os.get_terminal_size().columns - 1))
    FullPrint(f"There are currently {len(keys) - 1} connections active {buffer()}\n")
    if len(keys) > 1:
        statusLength += 1
        FullPrint("      ip(port)                       Last Request                Strikes    Instance")
    for key in keys.values():
        data = key.data
        if data:
            ipLog = ""
            statusLength += 1
            if time.time() - data.timeout < 100:
                addr, _ = addrConv(data)
                ipLog += addr + " " * (30 - len(addr)) + " " * 5
            else:
                addr, _ = addrConv(data)
                addr = "\33[5m" + addr + "\33[0m"
                ipLog += addr + " " * (38 - len(addr)) + " " * 5
            ipLog += data.lastReq + " " * (35 - len(data.lastReq)) + " " * 5
            strikeNum = ["Zero", "One", "Two", "Three", "Four", "Five"]
            ipLog += strikeNum[data.strikes] + " " * (11 - len(strikeNum[data.strikes]))
            ipLog += data.state + " " * (12 - len(data.state))
            ipLog += "|"
            FullPrint(ipLog)
    bannedListCopy = bannedList.copy()
    for host, expire in bannedListCopy.items():
        if expire - time.time() <= 0:
            del bannedList[host]
    if len(bannedList) > 0:
        if len(bannedList) == 1:
            FullPrint(f"\nThere is 1 currently banned ip:")
        else:
            FullPrint(f"\nThere are {len(bannedList)} currently banned ips:")
        statusLength += 2
        for host, expire in bannedList.items():
            statusLength += 1
            FullPrint(f"- {host}: {round(expire-time.time(), 1)} seconds remaining")
    for _ in range(statusLength):
        print("\033[F", end="")


try:
    while True:
        events = sel.select(timeout=0.1)
        if events:
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask)
        tick()
except KeyboardInterrupt:
    print("\n" * statusLength)
    FullPrint("Caught keyboard interrupt, exiting")
finally:
    sel.close()