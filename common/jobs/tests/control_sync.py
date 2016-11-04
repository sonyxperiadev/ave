from ave.network.connection import *
from ave.network.control    import Control, RemoteControl
from ave.network.pipe       import Pipe
from ave.network.exceptions import *

from setup import StepControl

def make_peers():
    sock,port = find_free_port()
    pipe      = Pipe()
    ctrl      = StepControl(port, 'password', sock, {'admin':None}, pipe, 0.1)
    conn      = BlockingConnection(('',port))
    ctrl.initialize()
    return conn, ctrl, pipe

def step_connect(conn, ctrl):
    conn.connect()
    ctrl.step_main() # detect new connection
    ctrl.step_main() # accept new connection

def step_authenticate(conn, ctrl, authkey):
    conn.put(make_digest(conn.get(), authkey))
    ctrl.step_main() # validate digest
    ctrl.step_main() # inform client
    finish_challenge(conn.get())

def step_call(conn, ctrl, payload):
    conn.put(payload)
    ctrl.step_main() # read message from client
    ctrl.step_main() # send response to client
    return json.loads(conn.get())

# just create and initialize a Control object (don't start it)
def t01():
    pretty = '%s t1' % __file__
    print(pretty)

    sock,port = find_free_port()

    try:
        ctrl = Control(port, 'password', sock, {'admin':None}, 1)
    except Exception, e:
        print('FAIL %s: could not create control: %s' % (pretty, e))
        return False

    try:
        ctrl.initialize()
    except Exception, e:
        print('FAIL %s: could not initialize control: %s' % (pretty, e))
        return False

    return True

# does Control.initialize create a non-blocking listening socket? check that
# Control.new_connection() gets called after running a couple of steps in the
# main loop. the number of steps should be deterministic because we are lock
# stepping both sides of the connection.
def t02():
    pretty = '%s t2' % __file__
    print(pretty)

    conn, ctrl, pipe = make_peers()

    try:
        conn.connect()
    except Exception, e:
        print('FAIL %s: could not connect to control: %s' % (pretty, e))
        return False

    try:
        ctrl.step_main() # detect new connection
        ctrl.step_main() # accept new connection
    except Exception, e:
        print('FAIL %s: could not detect/accept connection: %s' % (pretty, e))
        return False

    # expect to see an authentication challenge on the client side
    try:
        dig = conn.put(make_digest(conn.get(), 'password'))
    except Exception, e:
        print('FAIL %s: client could not handle challenge: %s' % (pretty, e))
        return False

    try:
        ctrl.step_main() # validate digest
        ctrl.step_main() # inform client
    except Exception, e:
        print('FAIL %s: could not authenticate client: %s' % (pretty, e))
        return False

    # expect to see an authentication success message on the client side
    try:
        msg = json.loads(conn.get())
    except Exception, e:
        print('FAIL %s: client could not get auth response: %s' % (pretty, e))
        return False
    if msg != { 'authenticated':True }:
        print('FAIL %s: not authenticated: %s' % (pretty, msg))
        return False

    # expect to see an indication that Control.new_connection() was called
    try:
        msg = pipe.get(timeout=1)
    except Empty:
        print('FAIL %s: indication not piped' % pretty)
        return False
    if msg != 'new_connection':
        print('FAIL %s: wrong indication on pipe: %s' % (pretty, msg))
        return False

    return True

# like t02 but fail the authentication and perform a full message exchange.
def t03():
    pretty = '%s t3' % __file__
    print(pretty)

    conn, ctrl, pipe = make_peers()

    # these steps should just work (see t02)
    try:
        step_connect(conn, ctrl)
        step_authenticate(conn, ctrl, 'wrong credentials')
    except AuthError:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong error: %s' % (pretty, e))
        return False

    # let the client make a remote function call on the control
    try:
        rpc = RemoteControl.make_rpc_blob('sync_ping', None)
        conn.put(rpc)
    except Exception, e:
        print('FAIL %s: could not put rpc blob: %s' % (pretty, e))
        return False

    try:
        ctrl.step_main() # read the rpc message
        ctrl.step_main() # write the rpc response
        msg = json.loads(conn.get())
        if msg != { 'result': 'pong' }:
            print('FAIL %s: wrong rpc response: %s' % (pretty, msg))
            return False
    except Exception, e:
        print('FAIL %s: could not process rpc: %s' % (pretty, e))
        return False

    return True

# like t03 but the rpc is asynchronous (only oob responses from server)
def t04():
    pretty = '%s t4' % __file__
    print(pretty)

    conn, ctrl, pipe = make_peers()

    try:
        step_connect(conn, ctrl)
        step_authenticate(conn, ctrl, 'wrong credentials')
    except AuthError:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong error: %s' % (pretty, e))
        return False
    pipe.get(timeout=1) # throw away new_connection indication

    # let the client make an asynchronous remote function call on the control
    try:
        rpc = RemoteControl.make_rpc_blob('async_ping', None, __async__=True)
        conn.put(rpc)
    except Exception, e:
        print('FAIL %s: could not put rpc blob: %s' % (pretty, e))
        return False

    try:
        ctrl.step_main() # read the rpc message
        msg = pipe.get(timeout=1)
        if msg != 'pong':
            print('FAIL %s: wrong pong: %s' % (pretty, msg))
            return False
    except Exception, e:
        print('FAIL %s: could not process rpc: %s' % (pretty, e))
        return False

    # do one last step to prove that the system is idle and won't send any more
    # responses
    try:
        ctrl.step_main() # call idle()
        msg = pipe.get(timeout=1)
        if msg != 'idle':
            print('FAIL %s: wrong idle: %s' % (pretty, msg))
            return False
        msg = conn.get(timeout=0.1) # raises ConnectionTimeout
    except ConnectionTimeout:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong error: %s' % (pretty, e))
        return False

    return True

# check that messages pushed by a controller are received even though the
# controller then goes on to .exit() itself.
def t05():
    pretty = '%s t5' % __file__
    print(pretty)

    conn, ctrl, pipe = make_peers()
    step_connect(conn, ctrl)
    step_authenticate(conn, ctrl, 'password')

    # call remote procedure
    rpc = RemoteControl.make_rpc_blob('raise_exit', None)
    conn.put(rpc)
    ctrl.step_main() # read the rpc message
    # ctrl.step_main() # no separate step to send exit message

    try:
        msg = conn.get(timeout=2)
    except Exception, e:
        print('FAIL %s: message not received: %s' % (pretty, str(e)))
        return False

    expected = { 'exception': {'message': 'passed to client', 'type': 'Exit'} }
    if json.loads(msg) != expected:
        print('FAIL %s: wrong response: %s' % (pretty, msg))
        return False

    msg = pipe.get(timeout=2) # throw away new_connection indication
    msg = pipe.get(timeout=2)
    if msg != 'shutdown':
        print('FAIL %s: wrong shutdown: %s' % (pretty, msg))
        return False

    return True

# try to break server-side authentication by sending the digest in multiple
# pieces.
def t06():
    pretty = '%s t6' % __file__
    print(pretty)

    conn, ctrl, pipe = make_peers()
    step_connect(conn, ctrl)
    digest = make_digest(conn.get(), 'password')

    # send the digest in multiple pieces to cause partial messages to be read
    # by the server. perform control steps in between partial reads to check
    # that the server does not hang.
    header = Connection.make_header(digest)
    conn.write(header[:2]) # send half the header
    ctrl.step_main()       # should be a noop
    conn.write(header[2:]) # send the rest of the header
    ctrl.step_main()       # should be a noop
    conn.write(digest[:5]) # send the first couple of bytes from the payload
    ctrl.step_main()       # should be a noop
    conn.write(digest[5:]) # send the rest of the payload
    ctrl.step_main()       # validate digest
    ctrl.step_main()       # inform client

    try:
        finish_challenge(conn.get())
    except AuthError:
        print('FAIL %s: wrong exchange caused authentication failure' % pretty)
        return False

    return True

# try to break the server-side processing of RPC messages by sending a message
# in multiple pieces.
def t07():
    pretty = '%s t7' % __file__
    print(pretty)

    conn, ctrl, pipe = make_peers()
    step_connect(conn, ctrl)
    step_authenticate(conn, ctrl, 'password')

    # send the message in multiple pieces to cause partial reads by the server.
    # perform control steps in between partial reads to check that the server
    # does not hang.
    payload = RemoteControl.make_rpc_blob('sync_ping', None)
    header  = Connection.make_header(payload)

    conn.write(header[:2])  # send half the header
    ctrl.step_main()        # should be a noop
    conn.write(header[2:])  # send the rest of the header
    ctrl.step_main()        # should be a noop
    conn.write(payload[:5]) # send the first couple of bytes from the payload
    ctrl.step_main()        # should be a noop
    conn.write(payload[5:]) # send the rest of the payload
    ctrl.step_main()        # validate and evaluate rpc
    ctrl.step_main()        # send response to client

    msg = conn.get(timeout=2)
    expected = { 'result':'pong' }
    if json.loads(msg) != expected:
        print('FAIL %s: wrong response: %s' % (pretty, msg))
        return False

    return True

# pass big mesages back and forth to check that the server doesn't get stuck on
# partial writes.
def t08():
    pretty = '%s t8' % __file__
    print(pretty)

    conn, ctrl, pipe = make_peers()
    step_connect(conn, ctrl)
    step_authenticate(conn, ctrl, 'password')

    # set the recv/send buffer sizes for all control connections to 1 byte.
    # this will normally result in buffer sizes of about 2 kilobytes.
    payload  = RemoteControl.make_rpc_blob('set_connection_buf_sizes',None,1024*64,1)
    response = step_call(conn, ctrl, payload)
    recv_size,send_size = tuple(response['result'])

    # craft a message that is just too big to send in one chunk
    payload  = RemoteControl.make_rpc_blob('sync_ping', None, '.'*send_size*30)
    conn.put(payload)
    ctrl.step_main() # read message from client

    # read the response back to the client. the server will need to perform a
    # number of steps in its main loop to get all the bytes out on the socket.
    response = ''
    while True:
        ctrl.step_main() # send response to client
        try:
            # reading non-blocking should never fail under these conditions,
            # except that data may not be available (raises ConnectionAgain).
            response += Connection.read(conn, send_size)
        except ConnectionAgain:
            continue
        except Exception, e:
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False
        try:
            size, payload = Connection.validate_message(response)
            result = json.loads(payload)
            break
        except Exception, e:
            pass # simply not done yet. do another step in the loop

    # check that the response is exactly what we sent
    if result['result'] != '.'*send_size*30:
        print('FAIL %s: wrong response' % pretty)
        return False

    return True

# try to break the server by making it return a message with garbage characters
def t09():
    pretty = '%s t9' % __file__
    print(pretty)

    conn, ctrl, pipe = make_peers()
    step_connect(conn, ctrl)
    step_authenticate(conn, ctrl, 'password')

    payload = RemoteControl.make_rpc_blob('make_garbage', None)
    header  = Connection.make_header(payload)

    conn.write(header + payload) # send the message

    try:
        ctrl.step_main() # let server receive the message
        ctrl.step_main() # let server send response to client
    except Exception, e:
        print('FAIL %s: could not step through garbage: %s' % (pretty, e))
        return False

    msg = conn.get(timeout=2)
    try:
        json.loads(msg)
    except Excpetion, e:
        print('FAIL %s: could not decode response: %s' % (pretty, e))
        return False

    return True

# TODO: check *ALL* possible call sites for Control.lost_connection(). this is
# only reported for fully established connections, so disconnects in any other
# states should *NOT* cause a call to Control.lost_connection().
